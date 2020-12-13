# BATCH LEVELLING IN GIMP
This guide was created to serve as a reference if batch auto or manual levelling is necessary in future. It was used in OCN001 to make the images look a bit nicer. Both manual and automatic levelling were required, so this serves as a guide to both.


## Requirements
- **GNU Parallel** is used in this guide, as GIMP's inbuilt batch-processing only utilises a single CPU core. A script utilising the inbuilt batch processing for automatic levelling is included in this folder (`batch-auto-levels.scm`), but unless you have troubles using Parallel, I wouldn't recommend using this one.
- Obviously, **GIMP** is required, but its scripting engine comes built-in.


## Installing the scripts so GIMP can find them
*n.b. this is liable to change with future versions of GIMP*
In my case, these scripts are located in `~/.config/GIMP/2.10/scripts/`. Simply copy the scripts there, or whatever is appropriate with future GIMP releases, and you're sweet!


## Auto-levelling 
### A single image
Auto-levelling is very simple, simply supply GIMP with a filename, and it does the rest. The syntax to do this with a single image from the command line is:

    gimp -i -b '(auto-levels "<path/to/image>")' -b '(gimp-quit 0)'

**WARNING:** This will overwrite the original image, so make sure you have a copy!


### Batch with GNU Parallel
To do this *en-masse*, we must pipe the names of the files to be processed into Parallel, and use `{}` within the command to specify where the filename (that was piped in) should be inserted. Note the escaped quotes (`\"`), which are necessary to make sure the shell passes the quotes through to Parallel, rather than interpreting them.

    find -name "*.png" | parallel --will-cite --progress --eta "gimp -i -b '(auto-levels \"{}\")' -b '(gimp-quit 0)'"
    

## Manual levelling
### A single image
Manual levelling is naturally a considerably more involved process. In total, GIMP's inbuilt manual levelling command takes 9 arguments! And that's only for a single colour channel...

The only two configurable parameters that have been maintained for this manual processing script are the low and high input intensities for each channel, as they are the only parameters that the auto-levelling tool modifies. The rest are hardcoded, but can be modified upon request. $5 per parameter ;) 

To find suitable values for these parameters, use the auto-levelling tool in the GIMP GUI (*Colors -> Levels, press 'Auto Input Levels'*), and observe the input levels for each channel. Frustratingly, while these levels are presented on the interval [0,255], the inbuilt levelling function expects them on [0,1], so you must perform this conversion manually.

Finally, to run the script:

    gimp -i -b '(manual-levels "<path/to/image>" <red-low-in> <red-high-in> <green-low-in> <green-high-in> <blue-low-in> <blue-high-in>)' -b '(gimp-quit 0)'
    
**WARNING:** This will overwrite the original image, so make sure you have a copy!


### Batch with GNU Parallel
Similar to above:

    find -name "*.png" | parallel --will-cite --progress --eta "gimp -i -b '(manual-levels \"{}\" <red-low-in> <red-high-in> <green-low-in> <green-high-in> <blue-low-in> <blue-high-in>)' -b '(gimp-quit 0)'"
    
