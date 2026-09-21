# Date:     21 September 2026
# Author:   Victoria Martinez
# Class:    DS 3022: UVA in Valencia
# Purpose:  connects to a local DuckDB file, loads YELLOW, GREEN and 
#           vehicle_emissions, prints raw row counts

# import libraries 
import duckdb
import os
import logging

# Sets up the load.log file to log the load process and applies to the whole script
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    filename='load.log'
)
logger = logging.getLogger(__name__)

# load URL given in class
BASE_URL = 'https://d37ci6vzurychx.cloudfront.net/trip-data'


def load_parquet_files():

    con = None

    try:
        # Connect to local DuckDB instance
        con = duckdb.connect(database='emissions.duckdb', read_only=False)
        con.execute("INSTALL httpfs; LOAD httpfs;")  # without this, read_parquet() can't hit the URL
        logger.info("Connected to DuckDB instance and loaded the needed httpfs extension")

        # One-time vehicle_emissions load — not tied to color/month, so it lives outside both loops
        con.execute("""
                    DROP TABLE IF EXISTS vehicle_emissions;
                    CREATE TABLE vehicle_emissions AS
                    SELECT * FROM read_csv_auto('data/vehicle_emissions.csv');
                    """)
        logger.info("Dropped and recreated vehicle_emissions from CSV")

        n = con.execute("SELECT COUNT(*) FROM vehicle_emissions").fetchone()[0]
        logger.info(f"vehicle_emissions: {n} rows loaded")

        for color in ["yellow", "green"]:  # loops over the two colors of trips
            table = f"{color}_trips"

            # Reset this color's table before rebuilding it across all 12 months
            con.execute(f"DROP TABLE IF EXISTS {table};")
            logger.info(f"Dropped {table} if it existed")

            for month in range(1, 13):  # inner loop per month, range is exclusive of upper limit
                url = f'{BASE_URL}/{color}_tripdata_2024-{month:02d}.parquet'
                try:
                    if month == 1:  # January defines the schema; rest insert into it
                        con.execute(f"""
                            CREATE TABLE {table} AS 
                            SELECT * FROM read_parquet('{url}');
                        """)
                        logger.info(f"Created table {table} from Parquet for month {month}")
                    else:
                        con.execute(f"""
                            INSERT INTO {table}
                            SELECT * FROM read_parquet('{url}');
                        """)
                        logger.info(f"Loaded {color} month {month:02d}")
                except Exception as month_error:
                    logger.error(f"Error loading {color} month {month:02d}: {month_error}")

            n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            logger.info(f"{table}: {n} rows loaded")

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