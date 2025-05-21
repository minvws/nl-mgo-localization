# Importing MedMij Lists

There are two types of MedMij List:
- ZAL ("ZorgAanbiederLijst", meaning healthcare provider list)
- ZKL ("ZorgaanbiederKoppelLijst", meaning healthcare provider relation list)

To import ZALs or ZKLs into the system, first obtain them from MedMij, then use the `organisation:import` cron command.


```shell
    $ python -m app.cron organisation:import <xml-file>
```

The import script will determine the type of MedMij List based on the XML and process it accordingly.
 Each MedMij List has a reference and timestamp which is used to mark the import, 
 in order for the system to be able to retrieve the latest version of the imported data.


