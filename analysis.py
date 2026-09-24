# Date last modified:   24 September 2026
# Author:               Victoria Martinez
# Class:                DS 3022: UVA in Valencia
# Purpose:              answers the six analysis questions and renders the CO2 plot 

# necessary libraries and imports
from pathlib import Path
import duckdb
import matplotlib.pyplot as plt
import logging

# set up log messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("analysis.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# add all of the needed constants 

PROJECT_DIRECTORY = Path(__file__).resolve().parent # needed to import PATH
DATABASE = PROJECT_DIRECTORY / "emissions.duckdb"
PLOT_FILE = PROJECT_DIRECTORY / "monthly_co2_totals.png"

TABLES = {
    "YELLOW": "yellow_trips",
    "GREEN": "green_trips"
}

# double check that these are the names of all of the columns 
REQUIRED_COLUMNS = {
    "pickup_time",
    "dropoff_time",
    "trip_distance",
    "trip_co2_kgs",
    "hour_of_day",
    "day_of_week",
    "week_of_year",
    "month_of_year"
}
# I started the week on a Sunday so that a Saturday ride was a "6"
DAY_NAMES = {
    0: "Sunday",
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday"
}
# these align with my clean.py months as well
MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December"
}

# all of the helper functions 

# Save as a true if the specified table exists 
def table_exists(con, table):

    result = con.execute("""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = ?
    """, [table]).fetchone()[0]

    return result == 1 

# Returns a set with all of the column names in a table 
def get_column_names(con, table):

    rows = con.execute(f"""
        DESCRIBE {table}
    """).fetchall() # not a [0] here - double check? 

    return {row[0] for row in rows}

# confirm that a transformed table is ready to be analyzed 
def validate_table(con, table):

    if not table_exists(con, table):
        raise RuntimeError(
            f"Required table {table!r} does not exist. Victoria, make sure that you ran load.py, clean.py, and transform.py first."
        )

    # for error messages
    existing_columns = get_column_names(con, table)
    missing_columns = REQUIRED_COLUMNS - existing_columns

    if missing_columns:
        raise RuntimeError(
            f"{table} is missing these required columns: "
            f"{sorted(missing_columns)}. Run transform.py first."
        )

    row_count = con.execute(f"""
        SELECT COUNT(*)
        FROM {table}
    """).fetchone()[0]

    # in case there are no rows, raise error
    if row_count == 0:
        raise RuntimeError(f"{table} contains no rows.")

    null_co2_count = con.execute(f"""
        SELECT COUNT(*)
        FROM {table}
        WHERE trip_co2_kgs IS NULL
    """).fetchone()[0]

    if null_co2_count != 0:
        raise RuntimeError(
            f"{table} contains {null_co2_count:,} rows with "
            "NULL trip_co2_kgs values."
        )

    # helpful message to make sure that I'm ready to move on
    print(
        f"{table}: validation passed "
        f"({row_count:,} rows available for analysis)"
    )


# -------------------- Analysis functions --------------------

# returns the single trip with the largest CO2 value
def report_largest_trip(con, cab_type, table):
    row = con.execute(f"""
        SELECT
            pickup_time,
            dropoff_time,
            trip_distance,
            trip_co2_kgs
        FROM {table}
        WHERE trip_co2_kgs IS NOT NULL
        ORDER BY
            trip_co2_kgs DESC,
            pickup_time ASC
        LIMIT 1
    """).fetchone()

    if row is None:
        print(f"{cab_type}: no trip was available.")
        return

    pickup_time, dropoff_time, distance, co2_kgs = row

    # I set up print statements with all of the necessary data
    print(f"{cab_type} largest carbon-producing trip:")
    print(f"  Pickup time: {pickup_time}")
    print(f"  Drop-off time: {dropoff_time}")
    print(f"  Trip distance: {distance:,.2f} miles")
    print(f"  Trip CO2: {co2_kgs:,.6f} kg")

# gets the highest and lowest average CO2 per trip
def get_heaviest_and_lightest(con, table, column):
    heaviest = con.execute(f"""
        SELECT
            {column} AS category_value,
            AVG(trip_co2_kgs) AS average_co2,
            COUNT(*) AS trip_count
        FROM {table}
        WHERE {column} IS NOT NULL
          AND trip_co2_kgs IS NOT NULL
        GROUP BY {column}
        ORDER BY
            average_co2 DESC,
            category_value ASC
        LIMIT 1
    """).fetchone()

    lightest = con.execute(f"""
        SELECT
            {column} AS category_value,
            AVG(trip_co2_kgs) AS average_co2,
            COUNT(*) AS trip_count
        FROM {table}
        WHERE {column} IS NOT NULL
          AND trip_co2_kgs IS NOT NULL
        GROUP BY {column}
        ORDER BY
            average_co2 ASC,
            category_value ASC
        LIMIT 1
    """).fetchone()

    return heaviest, lightest #return these

# I changed the 0-23 hour into the 1-24 hour numbering to make it easier for me to read
def format_hour(hour):
    return int(hour) + 1

# changes the numeric day into a day name
def format_day(day):
    return DAY_NAMES.get(int(day), f"Unknown day ({day})")

# formats a week number 
def format_week(week):
    return f"Week {int(week)}"

# formats the months into names correctly
def format_month(month):
    return MONTH_NAMES.get(int(month), f"Unknown month ({month})")

# reports the carbon-heaviest and carbon-lightest category.
def report_dimension(
    con,
    cab_type,
    table,
    column,
    label,
    formatter
):

    heaviest, lightest = get_heaviest_and_lightest(
        con,
        table,
        column
    )

    # to catch any errors in case it breaks
    if heaviest is None or lightest is None:
        print(f"{cab_type}: no results available for {label}.")
        return

    # set up the heaviest and lighest
    heavy_value, heavy_average, heavy_trip_count = heaviest
    light_value, light_average, light_trip_count = lightest

    print(f"{cab_type} {label}:")
    print(
        f"  Most carbon heavy: {formatter(heavy_value)} "
        f"with {heavy_average:,.6f} average kg CO2 per trip "
        f"across {heavy_trip_count:,} trips"
    )
    print(
        f"  Most carbon light: {formatter(light_value)} "
        f"with {light_average:,.6f} average kg CO2 per trip "
        f"across {light_trip_count:,} trips"
    )

# runs all 5 and sets up print statements so it's easier to read! 
def report_all_results(con):
    print("\n" + "=" * 72)
    print("TAXI CARBON EMISSIONS ANALYSIS")
    print("=" * 72)

    # seperated by question so that i can build upon each one and run
    # q.1 
    print("\n1. SINGLE LARGEST CARBON-PRODUCING TRIP")
    print("-" * 72)

    for cab_type, table in TABLES.items():
        report_largest_trip(con, cab_type, table)
        print()

    # q.2 
    print("\n2. MOST CARBON-HEAVY AND CARBON-LIGHT HOURS")
    print("-" * 72)

    for cab_type, table in TABLES.items():
        report_dimension(
            con=con,
            cab_type=cab_type,
            table=table,
            column="hour_of_day",
            label="hours of the day",
            formatter=format_hour
        )
        print()

    # q. 3
    print("\n3. MOST CARBON-HEAVY AND CARBON-LIGHT DAYS")
    print("-" * 72)

    for cab_type, table in TABLES.items():
        report_dimension(
            con=con,
            cab_type=cab_type,
            table=table,
            column="day_of_week",
            label="days of the week",
            formatter=format_day
        )
        print()

    # q. 4
    print("\n4. MOST CARBON-HEAVY AND CARBON-LIGHT WEEKS")
    print("-" * 72)

    for cab_type, table in TABLES.items():
        report_dimension(
            con=con,
            cab_type=cab_type,
            table=table,
            column="week_of_year",
            label="weeks of the year",
            formatter=format_week
        )
        print()

    # q. 5
    print("\n5. MOST CARBON-HEAVY AND CARBON-LIGHT MONTHS")
    print("-" * 72)

    for cab_type, table in TABLES.items():
        report_dimension(
            con=con,
            cab_type=cab_type,
            table=table,
            column="month_of_year",
            label="months of the year",
            formatter=format_month
        )
        print()

# Plotting functions 

# returns a list for each month's totals 
def get_monthly_totals(con, table):
    rows = con.execute(f"""
        SELECT
            month_of_year,
            SUM(trip_co2_kgs) AS total_co2
        FROM {table}
        WHERE month_of_year BETWEEN 1 AND 12
          AND trip_co2_kgs IS NOT NULL
        GROUP BY month_of_year
        ORDER BY month_of_year
    """).fetchall()

    totals_by_month = {
        int(month): float(total)
        for month, total in rows
    }
    return [
        totals_by_month.get(month, 0.0)
        for month in range(1, 13)
    ]

# time-series plot comparing the yellow and green
def create_monthly_plot(con):
    """
    Generate a time-series plot comparing monthly YELLOW and
    GREEN taxi CO2 totals.
    """

    months = list(range(1, 13))
    month_labels = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]

    yellow_totals = get_monthly_totals(
        con,
        TABLES["YELLOW"]
    )
    green_totals = get_monthly_totals(
        con,
        TABLES["GREEN"]
    )

    plt.figure(figsize=(12, 7))

    plt.plot(
        months,
        yellow_totals,
        color="#F4C430",
        marker="o",
        linewidth=2.5,
        label="Yellow taxis"
    )

    plt.plot(
        months,
        green_totals,
        color="#228B22",
        marker="o",
        linewidth=2.5,
        label="Green taxis"
    )

    plt.title(
        "Monthly Taxi Trip CO2 Totals - Project #1",
        fontsize=16,
        fontweight="bold"
    )

    plt.xlabel("Month", fontsize=12)
    plt.ylabel("Total CO2 (kg)", fontsize=12)

    plt.xticks(months, month_labels)
    plt.grid(
        axis="both",
        linestyle="--",
        alpha=0.4
    )

    plt.legend()
    plt.tight_layout()

    plt.savefig(
        PLOT_FILE,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print("\n6. MONTHLY CO2 TOTALS PLOT")
    print("-" * 72)
    print(f"Plot saved to: {PLOT_FILE}")


# -------------------- Main function --------------------

def analyze_data():
    """Connect to DuckDB, run the analysis, and create the plot."""

    con = None

    try:
        con = duckdb.connect(
            str(DATABASE),
            read_only=True
        )

        print(f"Connected to {DATABASE}")

        for table in TABLES.values():
            validate_table(con, table)

        report_all_results(con)
        create_monthly_plot(con)

        print("\nAnalysis completed successfully.")

    except Exception as error:
        print(f"\nAnalysis failed: {error}")
        raise

    finally:
        if con is not None:
            con.close()
            print("DuckDB connection closed.")


if __name__ == "__main__":
    analyze_data()