# Date last modified:   24 September 2026
# Author:               Victoria Martinez
# Class:                DS 3022: UVA in Valencia
# Purpose:              adds trip_co2_kgs, avg_mph, and the four date-part columns to the trips table

# this one was hard to debug so i added a lot of error and sample prints 
import logging
import duckdb

# set up log messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("transform.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# constants
DATABASE = "emissions.duckdb"
TABLES = ["yellow_trips", "green_trips"]
VEHICLE_TYPE_BY_TABLE = {
    "yellow_trips": "yellow_taxi",
    "green_trips": "green_taxi"
}

def table_exists(con, table):
    return con.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = ?
        """,
        [table]
    ).fetchone()[0] == 1

# check that the vehicle emissions are working, just as a precauion
def validate_emissions_table(con):
    if not table_exists(con, "vehicle_emissions"):
        raise RuntimeError(
            "vehicle_emissions does not exist. Run load.py first."
        )

    duplicate_types = con.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT vehicle_type
            FROM vehicle_emissions
            GROUP BY vehicle_type
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    # had to add this to check
    if duplicate_types != 0:
        raise RuntimeError(
            "vehicle_emissions has duplicate vehicle_type values. "
            "The CO2 lookup must return one rate per vehicle type."
        )

    null_rates = con.execute("""
        SELECT COUNT(*)
        FROM vehicle_emissions
        WHERE vehicle_type IS NULL
           OR co2_grams_per_mile IS NULL
    """).fetchone()[0]

    if null_rates != 0:
        raise RuntimeError(
            "vehicle_emissions contains NULL vehicle types or emission rates."
        )

# transform function 
def transform_table(con, table):
    logger.info("Starting transformations for %s", table)

    # adding one at a time
    # double check the data types! 
    con.execute(f"""
        ALTER TABLE {table}
        ADD COLUMN IF NOT EXISTS trip_co2_kgs DOUBLE
    """)

    con.execute(f"""
        ALTER TABLE {table}
        ADD COLUMN IF NOT EXISTS avg_mph DOUBLE
    """)

    con.execute(f"""
        ALTER TABLE {table}
        ADD COLUMN IF NOT EXISTS hour_of_day INTEGER
    """)

    con.execute(f"""
        ALTER TABLE {table}
        ADD COLUMN IF NOT EXISTS day_of_week INTEGER
    """)

    con.execute(f"""
        ALTER TABLE {table}
        ADD COLUMN IF NOT EXISTS week_of_year INTEGER
    """)

    con.execute(f"""
        ALTER TABLE {table}
        ADD COLUMN IF NOT EXISTS month_of_year INTEGER
    """)

    # The trip tables do not contain a vehicle_type column - had to hard code
    vehicle_type = VEHICLE_TYPE_BY_TABLE[table]

    matching_rates = con.execute("""
        SELECT COUNT(*)
        FROM vehicle_emissions
        WHERE vehicle_type = ?
    """, [vehicle_type]).fetchone()[0]

    if matching_rates != 1:
        available_values = con.execute("""
            SELECT vehicle_type, co2_grams_per_mile
            FROM vehicle_emissions
            ORDER BY vehicle_type
        """).fetchall()

        # added a runtime error here
        raise RuntimeError(
            f"{table}: expected exactly one emissions rate for "
            f"{vehicle_type!r}, but found {matching_rates}. "
            f"Available values: {available_values}"
        )

    # CO2 kilograms = miles * grams per mile / 1000.
    con.execute(f"""
        UPDATE {table}
        SET trip_co2_kgs =
            trip_distance * (
                SELECT co2_grams_per_mile
                FROM vehicle_emissions
                WHERE vehicle_type = ?
            ) / 1000.0
    """, [vehicle_type])

    # divided by 3600 to change to hours correctly
    con.execute(f"""
        UPDATE {table}
        SET avg_mph =
            CASE
                WHEN date_diff(
                    'second',
                    pickup_time,
                    dropoff_time
                ) > 0
                THEN trip_distance / (
                    date_diff(
                        'second',
                        pickup_time,
                        dropoff_time
                    ) / 3600.0
                )
                ELSE NULL
            END
    """)

    # update the table with the correct date data needed
    con.execute(f"""
        UPDATE {table}
        SET
            hour_of_day = CAST(
                date_part('hour', pickup_time) AS INTEGER
            ),
            day_of_week = CAST(
                date_part('dow', pickup_time) AS INTEGER
            ),
            week_of_year = CAST(
                date_part('week', pickup_time) AS INTEGER
            ),
            month_of_year = CAST(
                date_part('month', pickup_time) AS INTEGER
            )
    """)

    null_co2 = con.execute(f"""
        SELECT COUNT(*)
        FROM {table}
        WHERE trip_co2_kgs IS NULL
    """).fetchone()[0]

    null_date_parts = con.execute(f"""
        SELECT COUNT(*)
        FROM {table}
        WHERE hour_of_day IS NULL
           OR day_of_week IS NULL
           OR week_of_year IS NULL
           OR month_of_year IS NULL
    """).fetchone()[0]

    # added this to double check i wouldn't get weird data
    invalid_date_parts = con.execute(f"""
        SELECT COUNT(*)
        FROM {table}
        WHERE hour_of_day NOT BETWEEN 0 AND 23
           OR day_of_week NOT BETWEEN 0 AND 6
           OR week_of_year NOT BETWEEN 1 AND 53
           OR month_of_year NOT BETWEEN 1 AND 12
    """).fetchone()[0]

    nonpositive_duration = con.execute(f"""
        SELECT COUNT(*)
        FROM {table}
        WHERE date_diff(
            'second',
            pickup_time,
            dropoff_time
        ) <= 0
    """).fetchone()[0]

    # logger messages for null values
    logger.info(
        "%s NULL trip_co2_kgs values: %,d",
        table,
        null_co2
    )

    logger.info(
        "%s rows with NULL date parts: %,d",
        table,
        null_date_parts
    )

    logger.info(
        "%s rows with invalid date parts: %,d",
        table,
        invalid_date_parts
    )

    logger.info(
        "%s rows with nonpositive duration and NULL avg_mph: %,d",
        table,
        nonpositive_duration
    )

    if null_co2 != 0:
        raise RuntimeError(
            f"{table}: {null_co2:,} unexpected NULL CO2 values"
        )

    if null_date_parts != 0:
        raise RuntimeError(
            f"{table}: {null_date_parts:,} rows have NULL date parts"
        )

    if invalid_date_parts != 0:
        raise RuntimeError(
            f"{table}: {invalid_date_parts:,} rows have "
            "invalid date-part values"
        )

    sample = con.execute(f"""
        SELECT
            pickup_time,
            trip_distance,
            trip_co2_kgs,
            avg_mph,
            hour_of_day,
            day_of_week,
            week_of_year,
            month_of_year
        FROM {table}
        LIMIT 5
    """).fetchall()

    for row in sample:
        logger.info(
            "%s (%s) sample row: %s",
            table,
            vehicle_type,
            row
        )

    logger.info("Finished transformations for %s", table)

# transform data function with main entry point
def transform_data():
    con = None

    try:
        con = duckdb.connect(DATABASE, read_only=False)
        logger.info("Connected to %s", DATABASE)

        validate_emissions_table(con)

        for table in TABLES:
            if not table_exists(con, table):
                raise RuntimeError(
                    f"Required table {table} does not exist. "
                    "Run load.py and clean.py first."
                )

            con.execute("BEGIN TRANSACTION")

            try:
                transform_table(con, table)
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise

        logger.info("All trip tables transformed successfully") # yay!! 

    except Exception:
        logger.exception("Transformation failed")
        raise

    finally:
        if con is not None:
            con.close()
            logger.info("DuckDB connection closed")


if __name__ == "__main__":
    transform_data()