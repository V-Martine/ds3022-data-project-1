# Date:     21 September 2026
# Author:   Victoria Martinez
# Class:    DS 3022: UVA in Valencia
# Purpose:  connects to a local DuckDB file, loads vehicle_emissions and 
#           YELLOW trips for 2024 and prints out the raw row counts

# import necessary libraries 
import duckdb
import os
import logging

# Sets up the load.log file to log the load process and applies to the whole script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('load.log'), logging.StreamHandler()] # so I can see both of the log messages
)
logger = logging.getLogger(__name__)

# load URL given in class
BASE_URL = 'https://d37ci6vzurychx.cloudfront.net/trip-data'


def load_parquet_files():

    con = None

    try:
        # Connect to local DuckDB instance
        con = duckdb.connect(database='emissions.duckdb', read_only=False)
        con.execute("INSTALL httpfs; LOAD httpfs;")  # without this, the read_parquet() function will not work with the URL
        logger.info("Connected to DuckDB instance and loaded the needed httpfs extension")

        # One-time vehicle_emissions load, not tied to color/month, so it lives outside both loops
        con.execute("""
                    DROP TABLE IF EXISTS vehicle_emissions;
                    CREATE TABLE vehicle_emissions AS
                    SELECT * FROM read_csv_auto('data/vehicle_emissions.csv');
                    """)
        logger.info("Dropped and recreated vehicle_emissions from CSV")

        # ---------- vehicle_emissions (checkpoint 1) ----------
        con.execute("""
                    DROP TABLE IF EXISTS vehicle_emissions;
                    CREATE TABLE vehicle_emissions AS
                    SELECT * FROM read_csv_auto('data/vehicle_emissions.csv');
                    """)
        logger.info("Dropped and recreated vehicle_emissions from CSV")

        n = con.execute("SELECT COUNT(*) FROM vehicle_emissions").fetchone()[0]
        logger.info(f"vehicle_emissions: {n} rows loaded") # log message
        if n != 8:
            logger.warning(f"vehicle_emissions: expected 8 rows, got {n} — check the CSV") #sanity check in case there is a problem
        # -----------------------------------------------------------

         # ---------- yellow_trips and added green_trips working (checkpoint 2 & 3) ----------
        totals = {} # 
        
        # building a larger for loop to include the green and yellow 
        for color in ['yellow', 'green']:
            table = f"{color}_trips"

            # differentiating between yellow and green for clean.py and transform.py
            pickup_col = f"{'tpep' if color == 'yellow' else 'lpep'}_pickup_datetime"
            dropoff_col = f"{'tpep' if color == 'yellow' else 'lpep'}_dropoff_datetime"
            
            con.execute(f"DROP TABLE IF EXISTS {table};")
            logger.info(f"Dropped {table} if it existed")

            created = False  # flag to track if the table has been created

            # inner loop for the months
            for month in range(1, 13):
                url = f"{BASE_URL}/{color}_tripdata_2024-{month:02d}.parquet"

                # Wrote out explicit column lists and not a general SELECT *
                # We only need five specific columns (?) <- double check that once the second slidedeck comes out
                select_sql = f"""
                    SELECT
                        VendorID,
                        {pickup_col} AS pickup_time,
                        {dropoff_col} AS dropoff_time,
                        passenger_count,
                        trip_distance
                    FROM read_parquet('{url}')
                """
                try: 
                    before = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] if created else 0
                    
                    if not created:
                        con.execute(f"CREATE TABLE {table} AS {select_sql};")
                        created = True
                        logger.info(f"Created {table} table for month {month:02d}") #log messages
                    else:
                        con.execute(f"INSERT INTO {table} {select_sql};")
                        logger.info(f"Inserted data into {table} for month {month:02d}") #log messages
                    
                    after = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    added = after - before
                    logger.info(f"{table}: loaded month {month:02d}/2024 — {added:,} rows added (total {after:,})")

                    # sanity check for the added = 0 
                    if added == 0:
                        logger.warning(f"Added zero rows - no rows were added for {table} month {month:02d}. Check the month index.")
                
                except Exception as month_error:
                    logger.error(f"Error loading {color} month {month:02d}: {month_error}")
        
            if created: # enters if loop if at least one month was loaded successfully
                n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                logger.info(f"{table}: {n} rows loaded in total for 2024")
            else:
                logger.warning(f"No months were loaded successfully, table was never made")
        # ------ final summary messages ----------
        logger.info("----- RAW ROW COUNT SUMMARY -----")
        logger.info(f"vehicle_emissions: {n:,}")
        for t, c, in totals.items():
            logger.info(f"{t}: {c:,} rows loaded in total for 2024")

    except Exception as e:  # catches anything not caught in the inner per-month loop
        print(f"An error occurred: {e}")
        logger.error(f"An error occurred: {e}")

    finally:
        if con is not None:
            con.close()
            logger.info("DuckDB connection closed")


if __name__ == "__main__":
    load_parquet_files()


# -------------------------  CODE GRAVEYARD ---------------------------
# CODE SNIPPET FROM SLIDES: 
# con = duckdb.connect('emissions.duckdb', read_only=False)

# con.execute("""
#             DROP TABLE IF EXISTS vechicle_emissions;
#             CREATE TABLE vehicle_emissions AS 
#             SELECT * FROM  read_csv_auto('data/vehicle_emissions.csv');
#             """
# )

# n = con.execute(
#         "SELECT COUNT(*) FROM vehicle_emissions"
# ).fetchone()[0]
# logger.info(f"vehicle_emissions:{n} rows loaded")
# #https://d37ci6
# # for color in (yellow, green): for month in 1 - 12: INSERT


# con.execute(f"""
#                 DROP TABLE IF EXISTS {color}_trips;
#                 CREATE TABLE {color}_trips AS 
#                 SELECT * FROM read_parquet('{BASE_URL}/{color}_tripdata_2024-01.parquet');
#             """)
#             logger.info(f"Dropped table if exists and then created {color}_trips table from Parquet")

#             n = con.execute(f"SELECT COUNT(*) FROM {color}_trips").fetchone()[0]
#             logger.info(f"{color}_trips: {n} rows loaded")
#         con.execute(f"""
#             DROP TABLE IF EXISTS vechicle_emissions;
#             CREATE TABLE vehicle_emissions AS 
#             SELECT * FROM  read_csv_auto('data/vehicle_emissions.csv');
#         """)
#         logger.info("Dropped table if exists and then create vechicle_emissions table from CSV")

#         n = con.execute("SELECT COUNT(*) FROM vehicle_emissions").fetchone()[0]
#         logger.info(f"vehicle_emissions: {n} rows loaded")

#     except Exception as e:
#         print(f"An error occurred: {e}")
#         logger.error(f"An error occurred: {e}")
    
#     finally:
#         if con is not None:
#             con.close()
#             logger.info("DuckDB connection closed")

# if __name__ == "__main__":
#     load_parquet_files()

### from class snippet: 
# for month in range(1, 13):
#     for color in ['yellow', 'green']:
#         url = (
#             f'.../yellow_tripdata_2024-{month:02d}.parquet' if color == 'yellow' else
#             f'.../green_tripdata_2024-{month:02d}.parquet'
#         )
#         con.execute(f"""
#             INSERT INTO {color}_trips
#             SELECT * FROM read_parquet('{url}');
#         """)