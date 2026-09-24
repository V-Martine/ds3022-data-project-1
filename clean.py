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

def get_row_count(con, table_name):
    return con.execute(
        f"SELECT COUNT(*) FROM {table_name}"
    ).fetchone()[0]

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
        SELECT COUNT(*) 
        FROM {table_name}
        WHERE passenger_count = 0
    """).fetchone()[0]

    logger.info(
        "%s: %d zero-passenger trips before DELETE",
        table_name, before
    )

    con.execute(f"""
        DELETE FROM {table_name}
        WHERE passenger_count = 0
    """)

    after = con.execute(f"""
        SELECT COUNT(*)
        FROM {table_name}
        WHERE passenger_count = 0
    """).fetchone()[0]

    logger.info(
        "%s: %,d zero-passenger trips after DELETE", 
        table_name, 
        after
    )
    # log the number of duplicate rows removed
    logger.info(
        "%s: removed %d duplicate rows (from %d to %d)",
        table_name, before - after, before, after
    )

    if after != 0:
        raise RuntimeError(
            f"{table_name}: zero-passenger trips remain"
        )

    # ----------- Step #3: Removing the zer0-mile trips -------
    before = con.execute(f"""
        SELECT COUNT(*)
        FROM {table_name}
        WHERE trip_distance = 0
    """).fetchone()[0]

    logger.info(
        "%s: %d zero-mile trips before delete",
        table_name, 
        before
    )
    con.execute(f"""
        DELETE FROM {table_name}
        WHERE trip_distance = 0
    """)

    after = con.execute(f"""
        SELECT COUNT(*)
        FROM {table_name}
        WHERE trip_distance = 0                    
    """).fetchone()[0]

    logger.info(
        "%s: %d zero-mile trips after delete",
        table_name, 
        after
    )
    # log the number of duplicate rows removed
    logger.info(
        "%s: removed %d duplicate rows (from %d to %d)",
        table_name, before - after, before, after
    )

    if after != 0:
        raise RuntimeError(
            f"{table_name}: zero-mile trips remain"
        )
    
# --------- Step 4: Removing trips over 100 miles -----------
    before = con.execute(f"""
        SELECT COUNT(*)
        FROM {table_name}
        WHERE trip_distance > {MAX_TRIP_MILES}
    """).fetchone()[0]

    logger.info(
        "%s: %d trips over %d before delete",
        table_name, 
        before,
        MAX_TRIP_MILES
    )
    con.execute(f"""
        DELETE FROM {table_name}
        WHERE trip_distance > {MAX_TRIP_MILES}
    """)

    after = con.execute(f"""
        SELECT COUNT(*)
        FROM {table_name}
        WHERE trip_distance > {MAX_TRIP_MILES}                   
    """).fetchone()[0]

    logger.info(
        "%s: %d trips over %d miles after delete",
        table_name, 
        after,
        MAX_TRIP_MILES
    )
    # log the number of duplicate rows removed
    logger.info(
        "%s: removed %d duplicate rows (from %d to %d)",
        table_name, before - after, before, after
    )
    if after != 0:
        raise RuntimeError(
            f"{table_name}: trips over"
            f"{MAX_TRIP_MILES} miles remain"
        )
    # -------------- Step 5: Remove trips over 86,400 secs ----------
    before = con.execute(f"""
        SELECT COUNT(*)
        FROM {table_name}
        WHERE date_diff(
            'second',
            pickup_time, 
            dropoff_time
        ) > {MAX_TRIP_SECONDS}
    """).fetchone()[0]

    logger.info(
        "%s: %d trips over %d seconds before delete",
        table_name, 
        before,
        MAX_TRIP_SECONDS
    )
    con.execute(f"""
        DELETE FROM {table_name}
        WHERE date_diff(
            'second',
            pickup_time, 
            dropoff_time
        ) > {MAX_TRIP_SECONDS}
    """)

    after = con.execute(f"""
        SELECT COUNT(*)
        FROM {table_name}
        WHERE date_diff(
            'second',
            pickup_time, 
            dropoff_time
        ) > {MAX_TRIP_SECONDS}                  
    """).fetchone()[0]

    logger.info(
        "%s: %d trips over %d seconds after delete",
        table_name, 
        after,
        MAX_TRIP_SECONDS
    )
    # log the number of duplicate rows removed
    logger.info(
        "%s: removed %d duplicate rows (from %d to %d)",
        table_name, before - after, before, after
    )

    if after != 0:
        raise RuntimeError(
            f"{table_name}: trips over a day length remain"
        )
    
    final_count = get_row_count(con, table_name)

    logger.info(
        "%s: cleaning complete! %,d original rows, "
        "%,d final rows, %,d total rows removed", 
        table_name, 
        original_count, 
        final_count, 
        original_count - final_count
    )

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
            count = get_row_count(con, table)

            logger.info(
                "%s: %,d rows after cleaning",
                table,
                count
            )

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