import gc
import os
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.config.settings import (
    DRIVE,
    DB_PATH,
    MIN_AVAILABLE_RAM_MB,
    BATCH_SIZE
)

from backend.core.memory import (
    get_process_ram_mb,
    get_available_ram_mb,
    has_enough_ram
)

from backend.core.mft_scanner import (
    scan_mft
)

from backend.core.size_resolver import (
    SizeResolver
)

from backend.core.folder_analyzer import (
    build_folder_index
)

from backend.database.db import (
    create_connection,
    reset_database,
    insert_file_batch,
    get_file_count,
    get_folder_count
)

from backend.core.storage_scope import (
    StorageScopeClassifier
)

from backend.rules.base import (
    FileContext,
    SAFE_TO_CLEAN,
    PROTECTED,
    USER_VERIFICATION,
    AI_ANALYSIS,
)

from backend.rules.classifier import (
    StorageClassifier
)

from backend.rules.user_data_rules import (
    StandardUserFoldersRule
)

from backend.rules.protected_rules import (
    get_protected_rules
)

from backend.rules.safe_rules import (
    get_safe_rules
)

from backend.analysis.cleanup_classifier import (
    CleanupClassifier
)

from backend.analysis.cleanup_aggregator import (
    CleanupAggregator
)

from backend.ai_analysis.cluster_builder import (
    FolderTreeBuilder
)

from backend.ai_analysis.candidate_selector import (
    AdaptiveCandidateSelector
)

from backend.ai_analysis.pipeline import (
    AIAnalysisPipeline,
    AIAnalysisPipelineConfig,
)

from backend.ai_analysis.provider_factory import (
    AIProviderFactory
)

from backend.ai_analysis.provider_settings import (
    AIProviderSettings,
    APIKeyStore,
)

# ============================================================
# HELPER
# ============================================================

def bytes_to_gb(size):
    return size / (1024 ** 3)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 65)
    print("STORAGE MANAGER")
    print("=" * 65)


    # ========================================================
    # STEP 1 — RAM SAFETY CHECK
    # ========================================================

    available_ram = get_available_ram_mb()

    print(
        f"\nAvailable RAM: "
        f"{available_ram:.0f} MB"
    )


    if not has_enough_ram(
        MIN_AVAILABLE_RAM_MB
    ):

        print(
            "\n[ERROR] Not enough available RAM "
            "for safe MFT scanning."
        )

        return


    print(
        "[OK] RAM check passed."
    )


    initial_ram = (
        get_process_ram_mb()
    )


    # ========================================================
    # STEP 2 — DATABASE
    # ========================================================

    print(
        "\nPreparing database..."
    )


    conn = create_connection(
        DB_PATH
    )


    reset_database(
        conn
    )


    # ========================================================
    # STEP 3 — MFT SCAN
    # ========================================================

    print(
        "\nScanning MFT..."
    )


    entries, mft_time = scan_mft(
        DRIVE
    )


    total_mft = len(
        entries
    )


    mft_ram = (
        get_process_ram_mb()
    )


    print(
        f"MFT entries    : "
        f"{total_mft:,}"
    )

    print(
        f"MFT scan time  : "
        f"{mft_time:.2f} sec"
    )

    print(
        f"RAM after MFT  : "
        f"{mft_ram:.2f} MB"
    )


    # ========================================================
    # STEP 4 — SIZE RESOLVER
    # ========================================================

    size_resolver = (
        SizeResolver()
    )

    scope_classifier = (
    StorageScopeClassifier()
    )


    # ========================================================
    # STEP 5 — CLASSIFY + HYBRID SIZE + SQLITE
    # ========================================================

    print(
        "\nIndexing useful files..."
    )


    start = time.perf_counter()


    batch = []

    indexed_files = 0

    storage_classifier = StorageClassifier(
        user_rules=[StandardUserFoldersRule()],
        protected_rules=get_protected_rules(),
        safe_rules=get_safe_rules(),
    )

    cleanup_classifier = CleanupClassifier()
    cleanup_aggregator = CleanupAggregator()

    user_verification_files = []
    ai_analysis_files = []

    for entry in entries:

        # ----------------------------------------------------
        # MFT FIELDS
        # ----------------------------------------------------

        record_id = entry[0]

        path = entry[5]

        mft_size = entry[7]

        is_directory = entry[9]

        if is_directory:
            continue

        # ----------------------------------------------------
        # FULL WINDOWS PATH
        # ----------------------------------------------------

        full_path = (
            DRIVE + path
        )

        # ----------------------------------------------------
        # STORAGE SCOPE
        # ----------------------------------------------------

        scope = scope_classifier.classify(
            full_path
        )

        scope_value = scope.value

        # ----------------------------------------------------
        # HYBRID SIZE RESOLUTION
        #
        # MFT size > 0:
        #     Use MFT size
        #
        # MFT size == 0:
        #     os.path.getsize() fallback
        # ----------------------------------------------------

        accurate_size = (
            size_resolver.resolve(
                full_path,
                mft_size
            )
        )

        # ----------------------------------------------------
        # DETERMINISTIC CLASSIFICATION
        # ----------------------------------------------------

        classification_result = storage_classifier.classify(
            full_path,
            accurate_size
        )

        if classification_result is None:
            continue

        classification_name = (
            classification_result.classification
        )

        if classification_name == PROTECTED:
            continue

        # ----------------------------------------------------
        # ADD TO DATABASE BATCH
        # ----------------------------------------------------

        batch.append(
            (
                record_id,
                full_path,
                accurate_size,
                classification_name,
                scope_value
            )
        )

        indexed_files += 1

        if classification_name == SAFE_TO_CLEAN:

            cleanup_context = FileContext.create(
                full_path,
                accurate_size,
            )

            cleanup_item = cleanup_classifier.classify(
                cleanup_context,
                classification_result,
            )

            if cleanup_item is not None:
                cleanup_aggregator.add(
                    cleanup_item
                )

        elif classification_name == USER_VERIFICATION:
            user_verification_files.append(
                (full_path, accurate_size)
            )

        elif classification_name == AI_ANALYSIS:
            ai_analysis_files.append(
                (full_path, accurate_size)
            )

        # ----------------------------------------------------
        # WRITE BATCH
        # ----------------------------------------------------

        if len(batch) >= BATCH_SIZE:

            insert_file_batch(
                conn,
                batch
            )

            batch.clear()


    # ========================================================
    # WRITE REMAINING FILES
    # ========================================================

    if batch:

        insert_file_batch(
            conn,
            batch
        )


    conn.commit()


    indexing_time = (
        time.perf_counter()
        - start
    )


    print(
        f"Indexed files   : "
        f"{indexed_files:,}"
    )

    print(
        f"Indexing time   : "
        f"{indexing_time:.2f} sec"
    )

    print(
        f"RAM             : "
        f"{get_process_ram_mb():.2f} MB"
    )

    print(
        "\nCleanup summary:"
    )

    if cleanup_aggregator.get_groups():
        for group in cleanup_aggregator.get_groups():
            print(
                f"{group.action:<10} | "
                f"{group.files:6,} files | "
                f"{bytes_to_gb(group.size):8.2f} GB | "
                f"{group.category}"
            )
    else:
        print("No SAFE_TO_CLEAN files were classified.")

    print(
        f"User verification items : "
        f"{len(user_verification_files):,}"
    )

    print(
        f"AI analysis candidates  : "
        f"{len(ai_analysis_files):,}"
    )


    # ========================================================
    # STEP 6 — HYBRID SIZE STATISTICS
    # ========================================================

    size_stats = (
        size_resolver.get_stats()
    )


    print(
        "\nHybrid size resolution:"
    )


    print(
        f"MFT sizes used       : "
        f"{size_stats['mft_size_used']:,}"
    )

    print(
        f"Zero-size fallbacks  : "
        f"{size_stats['fallback_attempts']:,}"
    )

    print(
        f"Fallbacks fixed      : "
        f"{size_stats['fallback_fixed']:,}"
    )

    print(
        f"Actually empty files : "
        f"{size_stats['actual_empty_files']:,}"
    )

    print(
        f"Fallback failures    : "
        f"{size_stats['fallback_failed']:,}"
    )


    # ========================================================
    # STEP 7 — RELEASE MFT
    # ========================================================

    print(
        "\nReleasing MFT data..."
    )


    del entries

    gc.collect()


    ram_after_release = (
        get_process_ram_mb()
    )


    print(
        f"RAM after release: "
        f"{ram_after_release:.2f} MB"
    )


    # ========================================================
    # STEP 8 — BUILD FOLDER INDEX
    # ========================================================

    print(
        "\nBuilding folder index..."
    )


    folder_count, folder_time = (
        build_folder_index(
            conn
        )
    )


    print(
        f"Folders indexed     : "
        f"{folder_count:,}"
    )

    print(
        f"Folder analysis time: "
        f"{folder_time:.2f} sec"
    )


    # ========================================================
    # STEP 9 — AI ANALYSIS
    # ========================================================

    if ai_analysis_files:

        print(
            "\nRunning AI analysis pipeline..."
        )

        ai_settings = AIProviderSettings()
        ai_key_store = APIKeyStore()

        if not any(
            ai_key_store.has_api_key(provider)
            for provider in ai_settings.get_provider_order()
        ):
            print(
                "No AI provider credentials are configured; "
                "skipping AI analysis pipeline."
            )

        else:
            pipeline = AIAnalysisPipeline(
                settings=ai_settings,
                key_store=ai_key_store,
                config=AIAnalysisPipelineConfig(
                    max_rounds=2,
                    max_workers=2,
                ),
            )

            tree_builder = FolderTreeBuilder()
            candidate_selector = AdaptiveCandidateSelector()

            tree = tree_builder.build(
                ai_analysis_files
            )

            candidates = [
                node
                for node in tree.iter_nodes()
                if node.total_file_count > 0
            ]

            selection = candidate_selector.select(
                candidates
            )

            if selection.selected:
                result = pipeline.analyze(
                    selection.selected
                )

                print(
                    f"AI recommendations      : "
                    f"{len(result.safe_to_clean) + len(result.user_verification) + len(result.keep):,}"
                )

                if result.safe_to_clean:
                    print(
                        "AI SAFE_TO_CLEAN recommendations:"
                    )
                    for decision in result.safe_to_clean[:5]:
                        print(
                            f"  - {decision.cluster_path}"
                        )

                if result.user_verification:
                    print(
                        "AI USER_VERIFICATION recommendations:"
                    )
                    for decision in result.user_verification[:5]:
                        print(
                            f"  - {decision.cluster_path}"
                        )

            else:
                print("No AI analysis candidates were selected.")

    else:
        print(
            "\nNo AI_ANALYSIS files were classified."
        )

    # ========================================================
    # STEP 10 — TOP 20 LARGEST FOLDERS
    # ========================================================

    print(
        "\nTop 20 largest indexed folders:\n"
    )


    cursor = conn.execute(
        """
        SELECT
            path,
            total_size,
            total_file_count

        FROM folders

        ORDER BY total_size DESC

        LIMIT 20
        """
    )


    for (
        path,
        size,
        count

    ) in cursor:


        print(
            f"{bytes_to_gb(size):8.2f} GB | "
            f"{count:8,} files | "
            f"{path}"
        )


    # ========================================================
    # STEP 11 — IMPORTANT FOLDER VERIFICATION
    # ========================================================

    print(
        "\n" + "=" * 65
    )

    print(
        "IMPORTANT FOLDER CHECK"
    )

    print(
        "=" * 65
    )


    important_folders = [

        r"C:\Users\aashi\Downloads",

        r"C:\Users\aashi\AppData",

        r"C:\Users\aashi\AppData\Local",

        r"C:\Users\aashi\AppData\Roaming",

        r"C:\ProgramData"

    ]


    for folder_path in important_folders:


        cursor = conn.execute(
            """
            SELECT
                total_size,
                total_file_count

            FROM folders

            WHERE path = ?
            """,
            (
                folder_path,
            )
        )


        row = (
            cursor.fetchone()
        )


        if row:

            size, count = row


            print(
                f"\n{folder_path}"
            )

            print(
                f"  Size  : "
                f"{bytes_to_gb(size):.4f} GB"
            )

            print(
                f"  Files : "
                f"{count:,}"
            )


        else:

            print(
                f"\n{folder_path}"
            )

            print(
                "  Not found in index."
            )


    # ========================================================
    # STEP 12 — DATABASE SIZE
    # ========================================================

    db_size_mb = (

        os.path.getsize(
            DB_PATH
        )

        / 1024
        / 1024

    )


    # ========================================================
    # FINAL REPORT
    # ========================================================

    final_ram = (
        get_process_ram_mb()
    )


    total_processing_time = (

        mft_time

        + indexing_time

        + folder_time

    )


    print(
        "\n" + "=" * 65
    )

    print(
        "FINAL RESULTS"
    )

    print(
        "=" * 65
    )


    print(
        f"MFT entries       : "
        f"{total_mft:,}"
    )

    print(
        f"Files indexed     : "
        f"{get_file_count(conn):,}"
    )

    print(
        f"Folders indexed   : "
        f"{get_folder_count(conn):,}"
    )


    print()


    print(
        f"MFT scan          : "
        f"{mft_time:.2f} sec"
    )

    print(
        f"File indexing     : "
        f"{indexing_time:.2f} sec"
    )

    print(
        f"Folder analysis   : "
        f"{folder_time:.2f} sec"
    )

    print(
        f"Total processing  : "
        f"{total_processing_time:.2f} sec"
    )


    print()


    print(
        f"Initial RAM       : "
        f"{initial_ram:.2f} MB"
    )

    print(
        f"MFT peak RAM      : "
        f"{mft_ram:.2f} MB"
    )

    print(
        f"After MFT release : "
        f"{ram_after_release:.2f} MB"
    )

    print(
        f"Final RAM         : "
        f"{final_ram:.2f} MB"
    )


    print()


    print(
        f"Database size     : "
        f"{db_size_mb:.2f} MB"
    )


    print(
        "=" * 65
    )


    # ========================================================
    # CLOSE DATABASE
    # ========================================================

    conn.close()


if __name__ == "__main__":

    main()