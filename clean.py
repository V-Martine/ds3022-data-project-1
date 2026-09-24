# Date last modified:   24 September 2026
# Author:               Victoria Martinez
# Class:                DS 3022: UVA in Valencia
# Purpose:              Dedupes and removes invalid trips

# import needed libraries 
import duckdb
import logging

# sets up the clean.log file, also added terminal to make it easier to see
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('clean.log'), logging.StreamHandler()] # so I can see both of the log messages
)
logger = logging.getLogger(__name__)

# set up constants for cleaning
DATABASE = "emissions.duckdb"  # path to the DuckDB database file
TRIP_TABLES = ["yellow_trips", "green_trips"]  # list of trip tables to clean
MAX_TRIP_MILES = 100 # max trip distance, trips longer will be removed 
MAX_TRIP_SECONDS = 86_400  # max trip duration, trips longer will be removed

# created a cleaning function: 
def clean_trips_table(con, table_name):
    logger.info(f"Starting cleaning process for {table_name}") # so i know function was entered

    original_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0] # added the original count to know if anything was changed
    logger.info(f"{table_name}: {original_count} rows before cleaning")

    # ----------- Step #1: removing duplicate trips -----------
    temporary_table = f"{table_name}_clean"

    before = con.execute(
        f"SELECT COUNT(*) FROM {table_name}"
    ).fetchone()[0]

    con.execute(f"""
        CREATE TABLE {temporary_table} AS
        SELECT DISTINCT * FROM {table_name};
        DROP TABLE {table_name}; 
        ALTER TABLE {temporary_table} 
        RENAME TO {table_name};         
    """)
    print(f"Deduped {table_name} table and renamed to {table_name}_clean") # added this print statement so I can keep track of where we are better
    print(con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0], f"rows remain in {table_name} after deduplication" )

    after = con.execute(
        f"SELECT COUNT(*) FROM {table_name}"
    ).fetchone()[0]

    # log the number of duplicate rows removed
    logger.info(
        "%s: removed %d duplicate rows (from %d to %d)",
        table_name, before - after, before, after
    )

    # verify that there are duplicate rows remain and log a warning if so
    remaining_duplicate_groups = con.execute(f"""
        SELECT COUNT(*)
        FROM (
            SELECT *
            FROM {table_name}
            GROUP BY ALL
            HAVING COUNT(*) > 1
        ) AS duplicate_groups
    """).fetchone()[0]

    # log the number of remaining duplicate groups
    logger.info(
        "%s: duplicate groups remaining = %,d",
        table_name,
        remaining_duplicate_groups
    )

    # raise an error if there's still duplicate groups 
    if remaining_duplicate_groups != 0:
        raise RuntimeError(
            f"{table_name}: duplicate groups remain"
        )
    # ----- committed here at the end of class :), duplicates cleaned correctly! 
    
    # ----------- Step #2: 0-passenger trips -----------
    before = con.execute(f"""
        SELECT COUNT(*) FROM {table_name}
        WHERE passenger_count = 0
    """).fetchone()[0]
    print(before, f"rows with passenger_count = 0 will be removed from {table_name}") # same with this print statement 
    print(f'Before delete: {before:,} rows with passenger_count = 0')

    # ----------- Step #3: 


def clean_data():
    con = None

    try:
        # Connect to local DuckDB instance
        con = duckdb.connect(
            database=DATABASE, 
            read_only=False
        )
        
        logger.info("Connected to DuckDB instance")

        for table in TRIP_TABLES:
            # Check that load.py created the table before attempting to clean it
            table_exists =con.execute(
                """
                SELECT COUNT(*) 
                FROM information_schema.tables
                WHERE table_name = ?
                """, [table]
                ).fetchone()[0]
            
            if table_exists == 0:
                raise ValueError(f"Table {table} does not exist. Run load.py first.")
    
            con.execute("BEGIN TRANSACTION")

            try:
                clean_trips_table(con, table)
                con.execute("COMMIT")
                logger.info(f"Successfully cleaned {table}")
            except Exception as e:
                con.execute("ROLLBACK")
                logger.error(f"Error cleaning {table}: {e}")
                raise
        logger.info("Cleaning process completed successfully")

        for table in TRIP_TABLES:
            count = con.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

            logger.info(f"{table}: {count} rows after cleaning")
        
        logger.info("All trip tables cleaned successfully")

    except Exception as e:
        logger.error(f"Error during cleaning process: {e}")
        raise 

    finally:
        if con is not None:
            con.close()
            logger.info("Closed DuckDB connection")

if __name__ == "__main__":
    clean_data()