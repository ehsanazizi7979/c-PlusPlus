#!/usr/bin/env python3
"""Build the self-contained, eight-chapter + appendix study page from C__MUL~2.PDF.

Requires PyMuPDF and Pillow (the sandbox venv is ../.venv-doc):
    ../.venv-doc/bin/python chapter1-summary/build.py

The generated index.html embeds every figure as a data URI and every code
listing from chapters 1–8 and the appendix as highlighted, copyable <pre> blocks.
"""
from __future__ import annotations

import base64
import html
import io
import json
import re
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "C__MUL~2.PDF"
HERE = Path(__file__).resolve().parent
PAGE_OFFSET = 15  # PDF page 22 -> book page 7

# Each listing: (title, first line index, last line index, break-before indices)
# Indices refer to Courier-font lines extracted from that chapter in page order.
CHAPTER1_LISTINGS = [
    ("Hello world — TestDemo.cpp", 8, 15, set()),
    ("The four console entry-point prototypes", 16, 19, {17, 18, 19}),
    ("CalculateSomething — the UI-blocking pattern", 20, 28, set()),
    ("ComplexTest.cpp — six-parameter ComplexAdd", 31, 56, set()),
    ("Complex numbers with struct SComplex", 57, 88, set()),
    ("ComplexTestOO.cpp — the CComplex class", 91, 135, set()),
    ("friend operator+ declaration", 136, 137, set()),
    ("InheritanceTest.cpp — CPerson / CWorker / CStudent", 140, 199, set()),
    ("Inheritance and base-constructor snippets", 200, 207, {201, 202, 207}),
    ("PolymorphismTest.cpp — abstract CFigure and three shapes", 210, 307, set()),
    ("Base pointers and dynamic-binding snippets", 308, 317, {309, 311, 317}),
    ("Win32 GUI snippets — window setup and message loop", 320, 363,
     {321, 323, 325, 327, 330, 340, 344, 347, 351, 352, 353, 354, 361, 362, 363}),
    ("WndProc — the window's event handler", 364, 380, {367, 376}),
    ("CList.h — generic linked list", 383, 534, set()),
    ("CQueue.h — FIFO specialization", 538, 567, set()),
    ("CStack.h — LIFO specialization", 570, 599, set()),
    ("LinkedList.cpp — draining queue and stack", 601, 628, set()),
    ("Find with a class predicate — CStudent example", 629, 659, set()),
    ("Find with a free predicate — int example", 660, 678, set()),
]

CHAPTER2_LISTINGS = [
    ("ProcessDemo.cpp — launching Notepad with CreateProcess", 2, 26, set()),
    ("NtProcessDemo.cpp — reading the process information block", 29, 101, set()),
    ("PROCESS_BASIC_INFORMATION structure", 102, 108, set()),
    ("IPCWorker.cpp — worker side of the shared buffer", 112, 172, set()),
    ("IPCDemo.cpp — mutex + file mapping + two workers", 174, 336, set()),
    ("IPC API snippets from the explanation", 337, 348,
     {339, 340, 343, 344, 346}),
    ("PhilosophersDinner — stdafx.h", 351, 365, set()),
    ("PhilosophersDinner.cpp — semaphore-based table manager", 367, 577, set()),
    ("Philosopher — stdafx.h", 580, 584, set()),
    ("Philosopher.cpp — one process per philosopher", 586, 639, set()),
    ("Semaphore and console snippets", 640, 646, {643, 645, 646}),
    ("CreateThread prototype and start-routine typedef", 762, 766, {765}),
    ("CMySQL.h — database wrapper interface", 770, 796, set()),
    ("CMySQL.cpp — singleton connection and query methods", 798, 943, set()),
    ("MultithreadedDBTest.cpp — three threads, one critical section", 945, 1013, set()),
    ("MySQL table-locking alternative", 1014, 1024, {1017, 1021}),
    ("ConcurrentFileCopy.h — producer/consumer declarations", 1028, 1059, set()),
    ("ConcurrentFileCopy.cpp — two-thread file copy", 1061, 1314, set()),
    ("Write-only-when-data-available guard", 1315, 1321, set()),
    ("ThreadApp.h — user-mode driver loader", 1325, 1332, set()),
    ("ThreadApp.cpp — installing and starting the driver", 1335, 1431, set()),
    ("DriverApp.h — kernel driver entry points", 1434, 1436, set()),
    ("DriverApp.cpp — creating a system thread", 1439, 1486, set()),
    ("Kernel-thread explanation snippets", 1487, 1497,
     {1488, 1489, 1494, 1495, 1497}),
]

CHAPTER3_LISTINGS = [
    ("CreateThread and StartAddress prototypes", 0, 10, {8}),
    ("tmpThread.cpp — creating a thread and a process", 13, 52, set()),
    ("tmpProcess.cpp — the tiny child process", 58, 67, set()),
    ("CThread.h — abstract thread wrapper and CLock", 70, 125, set()),
    ("CThread.cpp — mutex, join, suspend/resume, state flags", 127, 268, set()),
    ("main.cpp — two window threads and Join", 270, 341, set()),
    ("AsyncThreads.cpp — four unsynchronised painters", 351, 496, set()),
    ("SyncThreads.cpp — four painters, one brush (STATE_SYNC)", 502, 647, set()),
    ("Mutex API — CreateMutex / OpenMutex / ReleaseMutex", 651, 663, {656, 661}),
    ("Semaphore API — Create/Open/ReleaseSemaphore", 664, 679, {670, 675}),
    ("Event API — CreateEvent/Ex, Open, Set, Reset, Pulse", 680, 705,
     {687, 692, 697, 700, 703}),
    ("Critical-section API — init, enter, leave, delete", 706, 721,
     {710, 713, 716, 719}),
]

# Figures: either an embedded image xref, or a vector clip rectangle to rasterise.
CHAPTER1_FIGURES = {
    "IMG_EXEC": {"page": 28, "clip": (132, 112, 480, 308)},
    "IMG_OBJECT": {"page": 38, "clip": (228, 140, 384, 650)},
}

CHAPTER2_FIGURES = {
    "CH2_FIG_1": {"page": 61, "xref": 145},   # single instruction pointer
    "CH2_FIG_2": {"page": 61, "xref": 146},   # four instruction pointers
    "CH2_FIG_3": {"page": 62, "xref": 149},   # progress over time
    "CH2_FIG_4": {"page": 64, "xref": 154},   # ProcessDemo screenshot
    "CH2_FIG_5": {"page": 66, "clip": (202, 112, 410, 226)},  # state diagram
    "CH2_FIG_6": {"page": 66, "xref": 159},   # PCB table
    "CH2_FIG_7": {"page": 70, "xref": 170},   # burn-buffer race
    "CH2_FIG_8": {"page": 72, "xref": 176},   # critical-section timeline
    "CH2_FIG_9": {"page": 81, "xref": 196},   # dining philosophers
    "CH2_FIG_10": {"page": 90, "xref": 216},  # process image
    "CH2_FIG_11": {"page": 91, "xref": 220},  # 3 processes
    "CH2_FIG_12": {"page": 92, "xref": 224},  # 1 process / 3 threads
}

CHAPTER4_LISTINGS = [
    ("basic_MPI.cpp — window messages, buttons and mouse move", 2, 124, set()),
    ("queue_MPI.cpp — four producers, one drawer, CQueue<PLOTDATA>", 128, 335, set()),
    ("Window user-data snippets — storing the queue", 338, 340, set()),
    ("threadMPI.cpp — PostThreadMessage and a thread message loop", 344, 486, set()),
    ("PeekMessage call that forces a thread queue", 489, 489, set()),
    ("pipe_server.cpp — named-pipe server with per-client threads", 492, 560, set()),
    ("pipe_client.cpp — opening the pipe and exchanging messages", 563, 597, set()),
    ("Named-pipe and WriteFile snippets from the explanation", 598, 601, {601}),
]

CHAPTER3_FIGURES = {
    "CH3_FIG_1": {"page": 124, "xref": 290},  # three processes in memory
    "CH3_FIG_2": {"page": 125, "xref": 293},  # one process, three threads
    "CH3_FIG_3": {"page": 126, "xref": 297},  # Windows thread object
}

CHAPTER5_LISTINGS = [
    ("basic_priority.cpp — UI thread above the drawing thread", 2, 161, set()),
    ("Storing the worker thread ID on the window", 162, 162, set()),
    ("concurrent_operations/main.h — QueueElement (mutex)", 166, 202, set()),
    ("concurrent_operations/main.cpp — mutex-protected queue", 204, 457, set()),
    ("CPU-count thread creation snippet", 458, 468, set()),
    ("concurrent_operations2/main.h — QueueElement (semaphore)", 472, 508, set()),
    ("concurrent_operations2/main.cpp — semaphore-limited workers", 510, 773, set()),
    ("Semaphore wait/release snippet", 774, 775, set()),
    ("concurrent_operations3/main.h — QueueElement (event)", 779, 815, set()),
    ("concurrent_operations3/main.cpp — event signals abort", 817, 1087, set()),
    ("concurrent_operations4/main.h — QueueElement (critical section)", 1091, 1127, set()),
    ("concurrent_operations4/main.cpp — critical-section workers", 1129, 1398, set()),
    ("concurrent_operations5/main.h — pipes, mutex, mapping", 1402, 1461, set()),
    ("concurrent_operations5/main.cpp — listener, workers, processes", 1462, 1785, set()),
    ("ClientProcess/main.cpp — solving an equation via the pipe", 1788, 1885, set()),
]

CHAPTER4_FIGURES = {}  # chapter 4 has no standalone illustrations in the PDF
CHAPTER5_FIGURES = {
    "CH5_FIG_1": {"page": 184, "xref": 417},  # base vs dynamic priority
}

CHAPTER6_LISTINGS = [
    ("CLRApplication/main.cpp — WinForms entry point (_tWinMain)", 2, 16, set()),
    ("CLRApplication/MyForm.h — Task + BeginInvoke cross-thread updates", 18, 121, set()),
    ("Cross-thread invoke and delegate snippets from the explanation", 122, 135,
     {122, 128, 131}),
    ("CLRApplication2/main.cpp — foreground Thread entry point", 138, 152, set()),
    ("CLRApplication2/MyForm.h — Thread with ParameterizedThreadStart", 154, 252, set()),
    ("IsBackground = true — turning a foreground Thread into background", 253, 256, set()),
    ("CLRApplication3/main.cpp — PostMessage example entry point", 259, 273, set()),
    ("CLRApplication3/MyForm.h — Sleep, END_TASK and the message loop", 275, 424, set()),
    ("User32.lib linker line from the explanation", 425, 425, set()),
    ("CLRApplication4/main.cpp — locked-variable example entry point", 428, 442, set()),
    ("CLRApplication4/MyForm.h — RAII Lock class with Monitor::Enter/Exit", 444, 624, set()),
    ("Concurrent enumeration of List<int> with two Tasks", 625, 650, set()),
    ("SafeValue — initonly field for safe concurrent reads", 651, 676, {651}),
    ("CLRApplication5/main.cpp — ManualResetEventSlim entry point", 679, 693, set()),
    ("CLRApplication5/MyForm.h — event replaces Sleep and shared flag", 695, 842, set()),
    ("WebClient EAP signatures with HostProtectionAttribute", 843, 851, set()),
    ("CLRApplication6/main.cpp — event-based factorial entry point", 854, 868, set()),
    ("CLRApplication6/MyForm.h — static EndTaskEvent and delegate fields", 870, 1043, set()),
    ("WebClient.DownloadDataAsync completion-handler snippet", 1044, 1065, {1044}),
    ("CLRApplication7/main.cpp — BackgroundWorker entry point", 1068, 1082, set()),
    ("CLRApplication7/MyForm.h — ProgressChanged and RunWorkerCompleted", 1084, 1188, set()),
    ("Derived Worker class overriding OnDoWork", 1189, 1215, set()),
    ("CLRApplication8/main.cpp — Thread::Abort example entry point", 1218, 1232, set()),
    ("CLRApplication8/MyForm.h — aborting a worker on form close", 1234, 1353, set()),
    ("CLRApplication9/main.cpp — safe cancellation entry point", 1356, 1370, set()),
    ("CLRApplication9/MyForm.h — WorkerSupportsCancellation + CancelAsync", 1372, 1497, set()),
    ("CancellationPending guard inside StartAddress", 1498, 1501, set()),
    ("Task::ContinueWith continuation snippet", 1502, 1510, {1504, 1507, 1510}),
    ("TestClass/TestWorker — why unsynchronised publication can fail", 1511, 1546, set()),
    ("Thread::MemoryBarrier full-fence version of Set/GetMethod", 1547, 1564,
     {1547, 1549, 1556}),
    ("volatile bState — half-fence version of TestClass", 1565, 1591, {1565, 1567}),
    ("CLRApplication10/main.cpp — Wait/Pulse example entry point", 1594, 1608, set()),
    ("CLRApplication10/MyForm.h — Monitor::Wait / Pulse with Lock", 1610, 1760, set()),
    ("CLRBarrier/main.cpp — Barrier example entry point", 1763, 1777, set()),
    ("CLRBarrier/MyForm.h — two participants, Parallel::Invoke, postPhaseAction",
     1779, 2008, set()),
]

CHAPTER6_FIGURES = {
    "CH6_FIG_1": {"page": 275, "xref": 606},  # deadlock traffic jam
}

CHAPTER7_LISTINGS = [
    ("Data race on iValue — two unsynchronised reads", 0, 4, {1, 3}),
    ("CLock class — mutex wrapper used throughout the chapter", 5, 23, set()),
    ("Inconsistent synchronisation — funcA and funcB use different locks",
     24, 36, set()),
    ("CList::Pop with only the assignment protected (incorrect)", 37, 59, set()),
    ("CList::Pop with both statements protected (correct)", 60, 82, set()),
    ("CBankAccount::Transfer — classic two-account deadlock", 83, 114, set()),
    ("ConcurrentDesign/stdafx.h — precompiled header", 117, 125, set()),
    ("Schwefel.h — CSchwefel interface and state", 127, 175, set()),
    ("Schwefel.cpp — sequential Evaluate", 177, 202, set()),
    ("CSchwefel::Initialize(void)", 203, 221, set()),
    ("CSchwefel::Initialize(unsigned uSize)", 222, 244, set()),
    ("CSchwefel::Elapsed(void)", 245, 255, set()),
    ("CSchwefel::Elapsed(TCHAR*)", 256, 269, set()),
    ("CSchwefel::Random — scaling rand() into the allele range", 270, 274, set()),
    ("SYSTEMTIME subtraction operator", 275, 298, set()),
    ("ConcurrentDesign.cpp — sequential program", 300, 310, set()),
    ("stdafx.h with SchwefelMT.h", 312, 321, set()),
    ("SchwefelMT.h — derived multi-threaded class", 323, 346, set()),
    ("CSchwefelMT::StartAddress — unsynchronised first attempt", 348, 375, set()),
    ("CSchwefelMT::Evaluate — CreateThread + WaitForMultipleObjects",
     376, 394, set()),
    ("ConcurrentDesign.cpp — sequential plus CSchwefelMT", 396, 409, set()),
    ("The unprotected dSum accumulation from the explanation", 410, 410, set()),
    ("Corrected StartAddress — thread-local values and one mutex per phase",
     411, 462, set()),
    ("CSchwefelP.h — OpenMP-derived class", 465, 483, set()),
    ("CSchwefelP.cpp — OpenMP parallel / reduction / critical", 485, 532, set()),
    ("stdafx.h with SchwefelMT.h and SchwefelP.h", 534, 544, set()),
    ("ConcurrentDesign.cpp — all three variants", 547, 563, set()),
]

CHAPTER7_FIGURES = {
    "CH7_FIG_1": {"page": 328, "xref": 713},  # interleaved Pop timing table
    "CH7_FIG_2": {"page": 331, "xref": 721},  # two-account deadlock timing
    "CH7_FIG_3": {"page": 344, "xref": 759},  # false sharing / lost update
    "CH7_FIG_4": {"page": 353, "xref": 782},  # console benchmark screenshot
}

CHAPTER8_LISTINGS = [
    ("ThreadPool/main.h — Windows and time headers", 2, 7, set()),
    ("CBankAccount.h — CLock and CParameters helpers", 9, 46, set()),
    ("CBankAccount.h — account state, LockName and Transfer", 47, 121, set()),
    ("CThread.h — simple worker-thread wrapper", 123, 162, set()),
    ("CThreadPool.h — the basic pool", 165, 262, set()),
    ("ThreadPool/main.cpp — twelve accounts, five transfers", 264, 299, set()),
    ("CThreadPool/main.h — MSG_ENDTASK and MAX_WAIT_TIME", 302, 309, set()),
    ("CBankAccount.h — helpers and account class", 311, 381, set()),
    ("CBankAccount::Transfer with the deliberate 100 ms Sleep", 382, 424, set()),
    ("CThread.h — worker plus monitored context thread", 426, 504, set()),
    ("CThreadPool.h — class, constructors and destructor", 507, 561, set()),
    ("CThreadPool.h — RemoveThread, WaitAll, RemoveAll, RequestThread",
     562, 638, set()),
    ("CThreadPool.h — InitializePool and the ProblemSolver loop", 639, 696, set()),
    ("CThreadPool/main.cpp — opposite transfers in a loop", 698, 722, set()),
    ("RemoteThreading/common.h — shared mapping and event names", 726, 733, set()),
    ("RemoteLoadLibrary — injecting LoadLibraryA into another process",
     735, 792, set()),
    ("RemoteFreeLibrary — unloading the DLL remotely", 793, 819, set()),
    ("RemoteThreading/main.cpp — launch calc.exe and drive the DLL",
     820, 854, set()),
    ("RemoteStartAddress DLL — find the main window and change its title",
     857, 935, set()),
    ("DllMain prototype from the explanation", 936, 937, set()),
]

CHAPTER8_FIGURES = {
    "CH8_FIG_1": {"page": 357, "xref": 797},  # thread pool overview
    "CH8_FIG_2": {"page": 369, "xref": 823},  # before/after dispatcher threads
    "CH8_FIG_3": {"page": 384, "xref": 855},  # problem solver monitors pool
    "CH8_FIG_4": {"page": 385, "xref": 859},  # deadlock detection screenshot
}

# The appendix has no C++ source listings; this single card preserves its
# verbatim URLs, include/lib paths and compiler/linker switches.
APPENDIX_LISTINGS = [
    ("Appendix setup URLs, paths and switches (verbatim)", 0, 24, set()),
]

APPENDIX_FIGURES = {
    "APP_FIG_1": {"page": 396, "xref": 885},   # Connector/C download page
    "APP_FIG_2": {"page": 397, "xref": 888},   # Connector/C setup wizard
    "APP_FIG_3": {"page": 398, "xref": 892},   # MySQL include directory
    "APP_FIG_4": {"page": 399, "xref": 896},   # libmysql.lib dependency
    "APP_FIG_5": {"page": 400, "xref": 900},   # WDK download page
    "APP_FIG_6": {"page": 400, "xref": 902},   # WDK installing
    "APP_FIG_7": {"page": 401, "xref": 906},   # WDK welcome
    "APP_FIG_8": {"page": 402, "xref": 910},   # Target extension .sys
    "APP_FIG_9": {"page": 402, "xref": 912},   # km include directory
    "APP_FIG_10": {"page": 403, "xref": 915},  # _X86_ / _AMD64_
    "APP_FIG_11": {"page": 404, "xref": 919},  # exceptions / runtime / GS-
    "APP_FIG_12": {"page": 404, "xref": 921},  # calling convention /Gz
    "APP_FIG_13": {"page": 405, "xref": 925},  # ntoskrnl.lib + hal.lib
    "APP_FIG_14": {"page": 406, "xref": 929},  # manifest / subsystem / driver
    "APP_FIG_15": {"page": 406, "xref": 931},  # entry point / base address
    "APP_FIG_16": {"page": 407, "xref": 935},  # DebugView kernel capture
    "APP_FIG_17": {"page": 408, "xref": 939},  # /MP multi-processor build
    "APP_FIG_18": {"page": 409, "xref": 943},  # /Qpar parallel code gen
    "APP_FIG_19": {"page": 410, "xref": 946},  # /openmp language support
}

CHAPTERS = [
    {"n": 1, "cache": "code_lines.json", "pages": range(22, 60),
     "min_lines": 679, "listings": CHAPTER1_LISTINGS, "start": 1},
    {"n": 2, "cache": "code_ch2.json", "pages": range(60, 120),
     "min_lines": 1498, "listings": CHAPTER2_LISTINGS, "start": 20},
    {"n": 3, "cache": "code_ch3.json", "pages": range(120, 156),
     "min_lines": 722, "listings": CHAPTER3_LISTINGS, "start": 44},
    {"n": 4, "cache": "code_ch4.json", "pages": range(156, 182),
     "min_lines": 602, "listings": CHAPTER4_LISTINGS, "start": 56},
    {"n": 5, "cache": "code_ch5.json", "pages": range(182, 248),
     "min_lines": 1886, "listings": CHAPTER5_LISTINGS, "start": 64},
    {"n": 6, "cache": "code_ch6.json", "pages": range(248, 324),
     "min_lines": 2009, "listings": CHAPTER6_LISTINGS, "start": 79},
    {"n": 7, "cache": "code_ch7.json", "pages": range(324, 356),
     "min_lines": 566, "listings": CHAPTER7_LISTINGS, "start": 114},
    {"n": 8, "cache": "code_ch8.json", "pages": range(356, 396),
     "min_lines": 942, "listings": CHAPTER8_LISTINGS, "start": 141},
    {"n": 9, "cache": "code_app.json", "pages": range(396, 412),
     "min_lines": 25, "listings": APPENDIX_LISTINGS, "start": 161},
]


def extract_code_lines(doc: pymupdf.Document, pages):
    """Courier-font lines at code indentation (>=120pt) in the given pages."""
    lines = []
    for page_no in pages:
        page = doc[page_no - 1]
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(span["text"] for span in line["spans"])
                if line["bbox"][0] >= 120 and any(
                    "Courier" in span["font"] for span in line["spans"]
                ):
                    lines.append({
                        "page": page_no,
                        "x": round(line["bbox"][0], 1),
                        "y": round(line["bbox"][1], 1),
                        "text": text.rstrip(),
                    })
    return lines


def listing_text(lines, start, end, breaks):
    out, prev = [], None
    for idx in range(start, end + 1):
        item = lines[idx]
        if prev is not None:
            gap = item["page"] != prev["page"] or item["y"] - prev["y"] > 18
            if idx in breaks or gap:
                out.append("")
        out.append(item["text"])
        prev = item
    return "\n".join(out)


def page_label(lines, start, end):
    first, last = lines[start]["page"], lines[end]["page"]
    b_first, b_last = first - PAGE_OFFSET, last - PAGE_OFFSET
    if first == last:
        return f"book p. {b_first} · PDF p. {first}"
    return f"book pp. {b_first}–{b_last} · PDF pp. {first}–{last}"


def render_code_cards(lines, listings, start_number):
    cards = []
    for number, (title, start, end, breaks) in enumerate(listings, start_number):
        code = html.escape(listing_text(lines, start, end, breaks))
        cards.append(f"""      <details class="code-card" open>
        <summary><span class="code-index">{number:02d}</span><span class="code-title">{html.escape(title)}</span><span class="code-pages">{page_label(lines, start, end)}</span><span class="chev">▼</span></summary>
        <div class="code-body"><div class="code-toolbar"><span>Verbatim listing from the PDF</span><button class="btn copy-btn">Copy code</button></div><pre><code class="language-cpp">{code}</code></pre></div>
      </details>""")
    return "\n".join(cards)


def render_figure(doc: pymupdf.Document, spec):
    if "xref" in spec:
        extracted = doc.extract_image(spec["xref"])
        data = extracted["image"]
        mime = "image/jpeg" if extracted["ext"].lower() in {"jpeg", "jpg"} else "image/png"
    else:
        pix = doc[spec["page"] - 1].get_pixmap(
            matrix=pymupdf.Matrix(3, 3),
            clip=pymupdf.Rect(*spec["clip"]),
            alpha=False,
            colorspace=pymupdf.csGRAY,
        )
        img = ImageOps.autocontrast(
            Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
        )
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        data, mime = buf.getvalue(), "image/png"
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def main():
    doc = pymupdf.open(PDF)
    replacements = {}

    for chapter in CHAPTERS:
        cache = HERE / chapter["cache"]
        if cache.exists():
            lines = json.loads(cache.read_text())
        else:
            lines = extract_code_lines(doc, chapter["pages"])
            cache.write_text(json.dumps(lines))
        assert len(lines) >= chapter["min_lines"], (
            f"chapter {chapter['n']}: unexpected extraction: {len(lines)} code lines"
        )
        prefix = {1: "CODE", 2: "CH2_CODE", 3: "CH3_CODE", 4: "CH4_CODE",
                  5: "CH5_CODE", 6: "CH6_CODE", 7: "CH7_CODE",
                  8: "CH8_CODE", 9: "APP_CODE"}[chapter["n"]]
        replacements[f"{{{{{prefix}_CARDS}}}}"] = \
            render_code_cards(lines, chapter["listings"], chapter["start"])
        replacements[f"{{{{{prefix}_COUNT}}}}"] = str(len(chapter["listings"]))

    for key, spec in {**CHAPTER1_FIGURES, **CHAPTER2_FIGURES, **CHAPTER3_FIGURES,
                      **CHAPTER4_FIGURES, **CHAPTER5_FIGURES, **CHAPTER6_FIGURES,
                      **CHAPTER7_FIGURES, **CHAPTER8_FIGURES,
                      **APPENDIX_FIGURES}.items():
        replacements["{{" + key + "}}"] = render_figure(doc, spec)

    template = (HERE / "template.html").read_text(encoding="utf-8")
    for key, value in replacements.items():
        template = template.replace(key, value)
    assert not re.search(r"\{\{(?:IMG|CH2|CH3|CH4|CH5|CH6|CH7|CH8|APP|CODE)[A-Z0-9_]*\}\}", template), "unfilled placeholder remains"
    assert "{data:image/" not in template, "malformed image data URI"

    output = HERE / "index.html"
    output.write_text(template, encoding="utf-8")
    print(f"wrote {output} ({output.stat().st_size:,} bytes; "
          f"{sum(len(c['listings']) for c in CHAPTERS)} listings, "
          f"{sum(len(f) for f in [CHAPTER1_FIGURES, CHAPTER2_FIGURES, CHAPTER3_FIGURES, CHAPTER4_FIGURES, CHAPTER5_FIGURES, CHAPTER6_FIGURES, CHAPTER7_FIGURES, CHAPTER8_FIGURES, APPENDIX_FIGURES])} figures)")


if __name__ == "__main__":
    main()
