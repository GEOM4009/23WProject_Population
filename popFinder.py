# -*- coding: utf-8 -*-
"""
Created on Wed Mar 15 20:54:35 2023.
Last updated on Thurs Mar 30, 2023.

@authors: Grace, Graham, Julien and Shaolin

This program will allow the user to calculate an estimated population that a flight path (and its buffer) intercepts.
The population is calculated from static population data (StatsCan table) and dynamic population data (TELUS table).
Once the user ends the program, all data that was not exported is lost and will need to be recalculated.

This is a user lead program and the user can decide to do 8 things
    1) Add flight paths
    2) Subset a 1 hour time frame
    3) Calculate the data 
    4) Print the calculated data in the console
    5) Export the calculated data as a csv
    6) Export the calculated data as a shapefile (note this will only contain all the lines that were added from choice number 1))
    7) View the map of all the dissemination areas and flight paths
    8) Export the map as a png -> Please note that this functionality is on hold at the moment since it needs webdrivers
                                                                                         
This program takes in 3 files
    1) A shapefile of dissemination areas with a DAUID and a DGUID columns
    2) A dynamic (TELUS) csv with a DGUID, timeframe_bucket (%Y-%m-%d  %I:%M %p), and a count columns
    3) A static (StatsCan) csv with a DAUID, POP_2016, POP_DENSITY and LANDAREA columns

If these files are not provided the tool will not work
Here is an example : run popFinder "./TestData/ExportedArea - Shapefile/ExportedAreas.shp" "./TestData/stat_can_data.csv" "./TestData/mock_telus_data.csv"

Known Problems:
    ARCGIS/ESRI shapefile cuts off the full column name for times.
"""
# -----------------------------------------------------IMPORTS
import argparse
import os

os.environ["USE_PYGEOS"] = "0"
import pandas as pd
import geopandas as gpd
from datetime import datetime
import fiona

from shapely.ops import unary_union

import folium

# For step 8 - if the user wants to use an existing web driver the png
# For exporting the map
# import io
# from PIL import Image

fiona.supported_drivers["LIBKML"] = "rw"

# -----------------------------------------------------GLOBAL VARIABLES
EXPECTED_HEADINGS_TELUS = [
    "input_requestId",
    "DGUID",
    "timeframe_bucket",
    "count",
]

EXPECTED_HEADINGS_STAT = [
    "DAUID",
    "POP_2016",
    "POP_DENSITY",
    "LANDAREA",
]  # DESNITY


EXPECTED_HEADINGS_SHAPE = ["DAUID", "DGUID"]

#Buffer 500 feet
#NOTICE - Buffer is not set to change - Perhaps in the future a buffer calculation function can be done
BUFFER = 152.4

# CRS for buffer calculations
CRS = "ESRI:102002"


#Flags
global DYNFLAG
DYNFLAG = False
global STATFLAG
STATFLAG = False

#For formatting numbers
pd.options.display.float_format = '{:,}'.format


# ----------------------------------------------------Checking data functions
def checkHeading(filepath):
    """
    ___Julien___
    This function checks if a csv file has actually been inputted, if not, it raises an error.
    If it is a csv, then it checks to see if it contains the expected headings.
    Returns a dataframe if it does or raises an exception if it does not.

    Tested using different valid and invalid csvs, works appropriately.

    Parameters
    ----------
    filepath : String
        A file path to a csv file

    Returns
    -------
    df : pandas dataframe
        The csv read into a pandas dataframe

    """
    if not filepath.endswith(".csv"):
        raise ValueError(f"Sorry, {filepath} is not a CSV file.")
    else:
        df = pd.read_csv(filepath)
        if all(item in list(df.columns) for item in EXPECTED_HEADINGS_TELUS):
            global DYNFLAG
            DYNFLAG = True
            return df
        elif all(item in list(df.columns) for item in EXPECTED_HEADINGS_STAT):
            global STATFLAG
            STATFLAG = True
            return df
        else:
            raise Exception(
                f"Sorry, {filepath} is missing one or more headings from one of these two lists: {EXPECTED_HEADINGS_TELUS}, {EXPECTED_HEADINGS_STAT}"
            )


def validAOI(filepath):
    """
    ___Graham___
    This function will check if the file is a valid kml.
    This function does not check whether the kml file contains a linestring, point, or polygon, because all
    three will work either way
    However, this function also does not check whether or not the kml intersects a dissemination area because it is possible for the buffer to intersect the area but not the line.
    Return True if valid
    Return False if not

    The function was tested by running in the command line with different file paths.
    A path to two different kml files was tested, all returned True.
    A gpkg file was tested for reference, it returned False.

    Parameters
    ----------
    filepath : String
        A filepath to a kml

    Returns
    -------
    bool
        If the kml is valid or not

    """
    print(filepath)
    assert os.path.exists(filepath), "I can not find the file at: " + str(
        filepath
    )
    if filepath.endswith(".kml"):
        return True
    else:
        return False


def validDate(date):
    """
    ___Shaolin___

    This function will check if the date is in the proper format of YYYY-MM-DD HH:MM P

    P in this case is either AM or PM

    This function was tested with the below code and worked:
    print (validdate ("2023-02-20 12:00 AM")) #prints True
    print (validdate ("2023-02-10 2:00 AM")) #prints True
    print (validdate ('2/26/2009 3:00 PM'))  # prints False, must have hyphens (-) not slashes (/)
    print (validdate ('21-11-06 2:00 AM'))  # prints False, must have 2021 not 21
    print (validdate ('2023-02-20  12:00:00 AM'))  # prints False, has extra seconds in string
    print (validdate ("2023-02-10 20:00 AM"))# prints False the hour must be in a 12-hour clock as a zero-padded decimal number (i.e. 01, 02, …, 12).

    Return True if valid
    Return False if not

    Parameters
    ----------
    date : String
        The input or desired date.

    Returns
    -------
    bool
        If the date is valid or not.

    """
    try:
        date == datetime.strptime(date, "%Y-%m-%d  %I:%M %p")
        return True
    except ValueError:
        return False


# --------------------------------------------------Creating data function
def calculate_stat(kml, shapefile, times):
    """
    ___Grace___
    Calculate the stats according to one kml file.

    Parameters
    ----------
    kml : String
        String to a valid kml
    shapefile : geo pandas df
        A GDF with population data - note that we are assuming that this shapefile has DAUID, POP_2016, and column names that match times
        *** In the future perhaps this should be an object! This way we know that it is in the proper format and we can add stuff to not recalculate the same data ***
    times : List of datetimes
        List of datetimes to calculate

    Returns
    -------
    temp_df : a geopandas df
        A gdf with the name of the kml, affected area (km^2), stat_pop, stat_density, and times + population density for the specified times

    """
    # First let's read the kml
    aoi = gpd.read_file(kml)
    aoi_gdf = aoi.to_crs(CRS)

    # Now create the buffer
    buff = aoi_gdf.buffer(BUFFER)
    area_buff = gpd.GeoDataFrame(geometry=gpd.GeoSeries(buff))

    # Get intersection
    subset = gpd.overlay(area_buff, shapefile, how="intersection")

    # Get area
    subset["intersectArea"] = subset.area
    subset = subset.to_crs(CRS)
    
    #Calculate weight and caluclate weighted pop
    subset["weight"] = subset["intersectArea"] / subset["Shape_Area"]
    subset["weightedPop"] = subset["POP_2016"] * subset["weight"]

    # Summing up everything
    areaSum = subset["intersectArea"].sum()
    popSum = subset["weightedPop"].sum()

    popSum = round(popSum)
    areaSum = round(areaSum / 1000000, 2)

    mergedPolys = unary_union(subset["geometry"])
    mergedPolys = aoi_gdf["geometry"]

    # Returning the one row
    temp_df = pd.DataFrame(
        [[kml, areaSum, popSum, round(popSum / areaSum, 5)]],
        columns=[
            "AOI_File_Name",
            "Affected_Area",
            "STAT_POP",
            "STAT_POP_DENSITY",
        ],
    )

    # Making it a geopandas instead of panada for mapping purposes
    temp_df = gpd.GeoDataFrame(
        temp_df, crs=CRS, geometry=gpd.GeoSeries(mergedPolys)
    )
    temp_df = temp_df.to_crs("EPSG:4326")

    temp_buffer = area_buff.to_crs("EPSG:4326")
    temp_df["Buffer_geometry"] = temp_buffer["geometry"]

    # Calculating data for each time
    for time in times:
        subset["weighted" + str(time)] = subset[str(time)] * subset["weight"]
        tempPopSum = subset["weighted" + str(time)].sum()

        tempPopSum = round(tempPopSum)

        time_df = pd.DataFrame(
            [[kml, tempPopSum, round(tempPopSum / areaSum, 5)]],
            columns=[
                "AOI_File_Name",
                "POP_" + str(time),
                "POP_DENSITY" + str(time),
            ],
        )

        # Merging it
        temp_df = pd.merge(temp_df, time_df, on="AOI_File_Name", how="outer")

    # Return merge
    return temp_df


# ------------------------------------------- Mapping functions
def choropleth_map(shp_df, aois, times, user_df):
    """
    ___Grace & Julien___
    This creates a map of calculated lines and the dissemination areas
    The dissemination areas appear as a choropleth map
    The lines appear as orange lines with their buffers

    Parameters
    ----------
    shp_df : a geopandas df
        The calculated shapefile that is created at the start of the tool
    aois : list of strings
        List of all AOIs the user has inputted -> this should match up with the recalculate function (will be solved with the recalculate)
    times : list of datetimes
        List of all times the user has inputted -> same as above
    user_df : geopandas df
        The calculated shapefile that is done by the recalculate function

    Returns
    -------
    m : folium.folium.Map
        A folium map with the dissemination areas and lines
        Please note that this only returns something for exporting -> which is something that is removed right now. If exporting is to stay removed then this should
        return nothing

    """

    # Initialize the Folium map with the first AOI as the center
    first_aoi = gpd.read_file(aois[0])
    m = folium.Map(
        location=[first_aoi.centroid.y, first_aoi.centroid.x],
        zoom_start=12,
        tiles="Stamen Terrain",
    )

    # Create a choropleth map based on the STAT_POP_DENSITY field
    # density_list = shp_df['POP_DENSITY'].tolist()
    # max_density = max(density_list)

    # Still deciding which is best
    # density_bins = [0, max_density * 0.2, max_density * 0.4, max_density * 0.6, max_density * 0.8, max_density]
    bins = list(shp_df["POP_DENSITY"].quantile([0, 0.25, 0.5, 0.75, 1]))

    # https://towardsdatascience.com/creating-choropleth-maps-with-pythons-folium-library-cfacfb40f56a
    folium.Choropleth(
        geo_data=shp_df,
        name="Population Density in Toronto",
        data=shp_df,
        columns=["DAUID", "POP_DENSITY"],
        key_on="feature.properties.DAUID",
        # fill_color='blue',
        fill_opacity=0.9,
        line_opacity=0.3,
        line_weight=3,
        legend_name="Population Density (people/km^2)",
        bins=bins,
        overlay=True,
    ).add_to(m)

    # Add the AOIs to the map as overlays
    for (
        _,
        r,
    ) in (
        user_df.iterrows()
    ):  # - https://gis.stackexchange.com/questions/397790/map-geopandas-dataframe-with-folium-no-results
        # This is the line
        sim_geo = gpd.GeoSeries(r["geometry"])
        geo_j = sim_geo.to_json()
        geo_j = folium.GeoJson(
            data=geo_j,
            style_function=lambda x: {
                "color": "orange",
                "fillColor": "#ff7800",
            },
        )

        # For hovering
        string = (
            "File Name: "
            + r["AOI_File_Name"]
            + "\n\n Affected Area: "
            + str(r["Affected_Area"])
            + "\n\n Static Population: "
            + str(r["STAT_POP"])
        )

        for time in times:
            string += (
                "\n\n Population at "
                + str(time)
                + " : "
                + str(r["POP_" + str(time)])
            )

        # This is a buffer
        sim_buff = gpd.GeoSeries(r["Buffer_geometry"])
        geo_b = sim_buff.to_json()
        geo_b = folium.GeoJson(
            data=geo_b,
            style_function=lambda x: {
                "color": "orange",
                "fillColor": "#ff7800",
                "opacity": 0.4,
            },
        )

        folium.Popup(string).add_to(geo_b)

        # Add buffer and line to map
        geo_b.add_to(m)
        geo_j.add_to(m)

    # Saving layers and map
    folium.LayerControl().add_to(m)
    m.save("map.html")

    print(type(m))
    return m


def main():
    # First let's create the data
    parser = argparse.ArgumentParser(
        prog="popFinder.py",
        description="Takes a shapefile of delimation areas, a csv filled with static population data and a csv filled with dynamic population data and allows the user to calculate population based off of areas of intersets and certain times",
    )

    parser.add_argument("DelAreaFile", help="The Delimination Area shapefile")
    parser.add_argument("StaticFile", help="The Static population data csv")
    parser.add_argument("DynamicFile", help="The Dynamic population data csv")
    args = parser.parse_args()

    # Now let's check that these are good files
    stat_df = checkHeading(args.StaticFile)
    dyn_df = checkHeading(args.DynamicFile)
    
    if(not DYNFLAG or not STATFLAG):
        raise Exception("Sorry Something went wrong when you inputed the static and dynamic population data")

    # Let's assume that all 3 files have interlapping DAUID and DGUID - since that is kind of on the user to know
    if not args.DelAreaFile.endswith('.shp'):
        raise ValueError("Sorry,"+ args.DelAreaFile + " is not a Shapefile file.")
    else:
        shp_df = gpd.read_file(args.DelAreaFile)
        if not all(item in list(shp_df.columns) for item in EXPECTED_HEADINGS_SHAPE):
            raise Exception("This shapefile does not have the proper coloumns")

    shp_df = shp_df.to_crs(CRS)
    shp_df["Shape_Area"] = shp_df.area

    # Creating the basic shapefile that we will use in calculations
    # Please note that this shapefile is not exportable or shareable since it's only used for calculations
    shp_df["DAUID"] = shp_df["DAUID"].astype(int)
    dyn_df["timeframe_bucket"] = pd.to_datetime(dyn_df["timeframe_bucket"])

    shp_df = pd.merge(
        shp_df,
        stat_df[["DAUID", "POP_2016", "POP_DENSITY"]],
        how="inner",
        on="DAUID",
    )

    # Let's store our AOIs
    aois = []
    # Let's store our times
    times = []

    # Let's store our calculations
    user_df = pd.DataFrame(columns=["AOI_File_Name"])

    # Now let's make the loop

    while True:
        # Prompt the user for input
        print("\n\n\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print("Please enter a number from the list below: ")
        print("\t1) to add a Area Of Interest")
        print("\t2) to add a time frame")
        print("\t3) to recalculate your data")
        print("\t4) to print your data")
        print("\t5) to export your data as a csv")
        print("\t6) to export your data as a shp ")
        print("\t7) to create and view your map")
        input_str = input(
            "Please enter some input, or type 'done' to finish: "
        )

        # If the user types "done", exit the loop
        if input_str == "done":
            break

        # Print the list of user input
        print("\n\nYou entered: " + input_str + "\n")

        # Add AOI
        if input_str == "1":
            input_aoi = input("Please enter your kml path: ")

            if validAOI(input_aoi):
                aois.append(input_aoi)
            else:
                print("This file was not valid")

        # Entering the times
        elif input_str == "2":
            input_date = input("Please enter your date and time: ")

            if validDate(
                input_date
            ):  # To add check if datatime is a time_bucket
                input_date = datetime.strptime(
                    input_date, "%Y-%m-%d  %I:%M %p"
                )
                # Add it to shapefile
                dd = dyn_df.loc[dyn_df["timeframe_bucket"] == input_date]

                if dd.empty:
                    print(
                        "The date you entered is not in the dynamic file. Please try again"
                    )
                else:
                    times.append(input_date)
                    dd = dd[["DGUID", "count"]]
                    dd = dd.rename(columns={"count": str(input_date)})
                    shp_df = pd.merge(shp_df, dd, how="inner", on="DGUID")

            else:
                print("This date format was not valid")

        # Recalculating table
        elif input_str == "3":
            # First let's reset the table
            old_df = user_df.copy()  # In case something goes wrong
            user_df = pd.DataFrame(columns=["AOI_File_Name"])

            try:
                for kml in aois:
                    # temp_df = calculate_stat(kml, test, stat_df, dyn_df, times)
                    temp_df = calculate_stat(kml, shp_df, times)
                    user_df = pd.concat([user_df, temp_df], sort=False)
            except:
                print("Something went wrong when calculating - resetting old")
                print(
                    "As of this moment the best way to fix this problem is to restart the entire program"
                )
                user_df = old_df

        # Printing the table
        elif input_str == "4":
            with pd.option_context(
                "display.max_rows", None, "display.max_columns", None
            ):  # More options can be specified also - https://stackoverflow.com/questions/11707586/how-do-i-expand-the-output-display-to-see-more-columns-of-a-pandas-dataframe
                print(user_df)

        # Exporting data as csv
        # AS DISCUSSED -> We will not output the geometry, since the numbers is the desired output
        elif input_str == "5":
            csv_df = user_df.copy()
            csv_df = csv_df.drop(columns=["Buffer_geometry", "geometry"])
            try:
                csv_df.to_csv("FlightPath.csv")
            except Exception as e:
                print("Something went wrong")
                print(e)

        # Exporting data as shapefile
        # As discussed -> We will output the lines (NOT THE BUFFER) as the shapefile
        elif input_str == "6":
            sh_gdf = user_df.copy()
            sh_gdf = sh_gdf.drop(columns=["Buffer_geometry"])
            sh_gdf = gpd.GeoDataFrame(
                sh_gdf, crs=CRS, geometry=sh_gdf["geometry"]
            )

            try:
                sh_gdf.to_file("FlightPath.shp")
            except Exception as e:
                print("Something went wrong")
                print(e)

        # This calculates and makes an html page of the map
        elif input_str == "7":
            map_out = choropleth_map(shp_df, aois, times, user_df)

        elif input_str == "8":
            # https://stackoverflow.com/questions/53565979/export-a-folium-map-as-a-png
            # PLEASE NOTE: FOLIUM does not have a good export png function. One must open the map and then take a screenshot.
            # We are asking today (2023/03/30) if the html page is what is wanted - OR - if the program could have access to webdrivers so that the user can export to png.
            continue

        else:
            print("\n Not a valid input")


if __name__ == "__main__":
    main()
