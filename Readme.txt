# Population Project
------------------------------------------------------

Created on Wed March 15 20:54:35 2023
Last updated on Wed April 12, 2023

@authors: Grace Thompson, Graham Scott, Julien Belair and Shaolin Gawat

This program will allow the user to calculate an estimated population that a flight path (and it's buffer) intercepts.
The population is calculated from static population and dynamic population data.
Once the user ends the program, all data that was not exported is lost and will need to be recalculated.

------------------------------------------------------
~~~~ INSTALLATION  ~~~~

In the Anaconda Prompt and In the directory with the environment.yml file (home directory) enter:
    conda env create -f environment.yml

This may take a few minutes.
Once finished activate the environment:
    conda activate popFinder_env
    
If you run into any problems please consult to https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html
 
 ------------------------------------------------------
 ~~~~ STARTING THE PROGRAM ~~~~
 
 In the Anaconda  Prompt please enter the following:
    run popFinder.py 'Path_To_Shapefile.shp', 'Path_To_Static_csv', 'Path_To_Dynamic.csv'

Where:
    'Path_To_Shapefile.shp' : A shapefile of dissemination areas with a DAUID and a DGUID columns
    'Path_To_Static_csv': A static (Stat CAN) csv with a DAUID, POP_2016, POP_DESNITY and LANDAREA columns
    'Path_To_Dynamic.csv': A dynamic (Telus) csv with a DGUID, timeframe_bucket (%Y-%m-%d  %I:%M %p) and a count columns

Example: 
    run popFinder "./TestData/ExportedArea - Shapefile/ExportedAreas.shp" "./TestData/stat_can_data.csv" "./TestData/mock_telus_data.csv"
    
------------------------------------------------------
~~~~ USING THE PROGRAM ~~~~

This is a user lead program and the user can decide to do 7 actions
    1) Add flight paths (as kml files)
    2) Add a 1 hour time frame (%Y-%m-%d  %I:%M %p Or YYYY-MM-DD HH:MM P (where p is AM or PM)
    3) Calculate the data 
    4) Print the calculated data in the console
    5) Export the calculated data as a csv (called FlightPath.csv)
    6) Export the calculated data as a geopackage 
    7) View the map of all the dissemination areas and flight paths

~~ IMPORTANT NOTE ~~
Once you enter 'done', all the data the program calculated will be lost! 
Please export your work!
                                                                                         
------------------------------------------------------
~~~~ WANT MORE INFO ~~~~
Want to know more about the project? Please refer to the GEOM 4009 Team Report file!
Any Questions and/or troubles? Please refer to the GEOM 4009 Team Report FAQ section.
Want to know more about the functions the program uses? Open PopulationProj\docs\_build\html and view index.html.


------------------------------------------------------
~~~ KNOWN ISSUES ~~~~
 - When calculating the data (3) or making the map (7), warnings about Geometry is in a geographic CRS. Results from 'centroid' are likely incorrect. 
    From our tests this does not affect the population and are currently looking into changing our CRS
 - When making the map (7) 'FutureWarning: Calling float on a single element Series is deprecated and will raise a TypeError in the future' appears. 
    Note this is a feature folium is planning on adding in the future. Using the environment, no TypeError should appear. 
 
 ------------------------------------------------------
~~~ PopulationProjectFinal Direcorty Setup ~~~
CompletedData
    FlightPath.csv -> An example of a csv from (5) Export the calculated data as a csv
    FlightPath.gpkg -> An example of gpkg from (6) Export the calculated data as a geopackage
    HowToCreate.txt -> An example of user input (along with the programs output)
    OtherTests.txt -> What other tests were performed when testing the popFinder.py file
    map.html -> An example of a html output from (7) View the map of all dissemination areas and     flight paths

 TestData
    All Toronto - Shapefile
        AllToronto.shp (and associated  ESRI shapefile files) -> Shapefile of all dissemination         areas in Toronto
    ExportedAreas - Shapefile
        ExportedAreas.shp (and associated ESRI shapefile files) -> Shapefile of 11 dissemination         areas in Toronto
    TestShapefile
        africa_countries_ESRI.shp (and associated ESRI shapefile files) -> Shapefile (by ESRI)           of African Countries (For testing shapefiles with no DAUID of DGUID)
     Test2KML.kml -> A line kml file going through Toronto
     TestPath.kml -> A line kml file going through Toronto
     TestPoints.kml -> Points around Toronto 
     TestPolygons.kml -> A polygon around Toronto
     mock_telus_data.csv -> A mock dynamic file that could be used
     stat_can_data.csv -> A static data file that could be used (Population from Statistics          Canada 2016)

docs -> Sphinx Documentation about PopFinder. Please note that Sphinx auto documentation is removed from this version of the code, perhaps in a future version it would be reinstated. 

This is to view the functions in popFinder.py. Open up ./docs/_build/index.html to view. 
Perhaps in the future, full sphinx documentation could be reinstated.

But as it was not requested by our client, we've decided to keep it out
    Readme.txt -> Gives information about the entire project
    environment.yml -> the conda environment (Please see above about how to get started)
    licence.txt -> the license of this project
    popFinder.py-> The main file in this project. This file will allow you to find the estimated
    population in dissemination areas from both static and dynamic data
 
     
