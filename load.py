# Date:     21 September 2026
# Author:   Victoria Martinez
# Class:    DS 3022: UVA in Valencia
# Purpose:  CHECKPOINT #1 VEHICLE_EMISSIONS_ LOADED

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
        con = duckdb.connect(database='emissions.duckdb', read_only=False)
        con.execute("INSTALL httpfs; LOAD httpfs;")
        logger.info("Connected to DuckDB instance and loaded the httpfs extension")

        con.execute("""
                    DROP TABLE IF EXISTS vehicle_emissions;
                    CREATE TABLE vehicle_emissions AS
                    SELECT * FROM read_csv_auto('data/vehicle_emissions.csv');
                    """)
        logger.info("Dropped and recreated vehicle_emissions from CSV")

        n = con.execute("SELECT COUNT(*) FROM vehicle_emissions").fetchone()[0]
        logger.info(f"vehicle_emissions: {n} rows loaded")

        if n != 8:
            logger.warning(f"vehicle_emissions: expected 8 rows, got {n} — check the CSV")

    except Exception as e:
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

# vehicle_emissions checkpoint: 
