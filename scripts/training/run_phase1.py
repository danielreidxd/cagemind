
import argparse
import sys
import time
from datetime import timedelta

from config.settings import setup_logging

logger = setup_logging("phase1_runner")


def run_step_1():
    """Paso 1: Scraping de peleadores."""
    logger.info("🥊 PASO 1: Scraping de peleadores desde UFCStats.com")
    from data.scrapers.ufcstats_fighters import scrape_all_fighters
    fighters = scrape_all_fighters()
    logger.info(f"✅ Paso 1 completado: {len(fighters)} peleadores")
    return fighters


def run_step_2():
    """Paso 2: Scraping de eventos y peleas."""
    logger.info("🥊 PASO 2: Scraping de eventos y peleas")
    from data.scrapers.ufcstats_events import scrape_all_events
    events, fights = scrape_all_events()
    logger.info(f"✅ Paso 2 completado: {len(events)} eventos, {len(fights)} peleas")
    return events, fights


def run_step_3():
    """Paso 3: Scraping de estadísticas detalladas."""
    logger.info("🥊 PASO 3: Scraping de estadísticas round-by-round")
    from data.scrapers.ufcstats_fight_stats import scrape_all_fight_stats
    stats = scrape_all_fight_stats()
    logger.info(f"✅ Paso 3 completado: {len(stats) if stats else 0} peleas con stats")
    return stats


def run_step_4():
    """Paso 4: Pipeline de limpieza y carga."""
    logger.info("🥊 PASO 4: Limpieza, carga a SQLite y exportación a CSV")
    from data.scrapers.pipeline import run_pipeline
    run_pipeline()
    logger.info("✅ Paso 4 completado: datos en SQLite + CSVs exportados")


def main():
    parser = argparse.ArgumentParser(
        description="UFC Fight Predictor — Fase 1: Recolección de Datos"
    )
    parser.add_argument(
        "--step",
        type=int,
        choices=[1, 2, 3, 4],
        help="Ejecutar solo un paso específico (1-4). Sin este flag, se ejecutan todos.",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("UFC FIGHT PREDICTOR — FASE 1")
    logger.info("Recolección de Datos desde UFCStats.com")
    logger.info("=" * 60)

    start_time = time.time()

    try:
        if args.step:
            steps = {1: run_step_1, 2: run_step_2, 3: run_step_3, 4: run_step_4}
            steps[args.step]()
        else:
            run_step_1()
            run_step_2()
            run_step_3()
            run_step_4()

        elapsed = timedelta(seconds=int(time.time() - start_time))
        logger.info("=" * 60)
        logger.info(f"🏆 FASE 1 COMPLETADA en {elapsed}")
        logger.info("=" * 60)
        logger.info("Próximo paso: Fase 2 — Análisis Exploratorio")
        logger.info("  python -m notebooks.eda  (o abre los Jupyter notebooks)")

    except KeyboardInterrupt:
        logger.info("\n⏸️  Scraping interrumpido por el usuario.")
        logger.info("Los checkpoints se guardaron — puedes reanudar ejecutando el mismo comando.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}", exc_info=True)
        logger.info("Revisa los logs en la carpeta logs/ para más detalles.")
        sys.exit(1)


if __name__ == "__main__":
    main()
