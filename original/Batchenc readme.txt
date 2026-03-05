What's new in v1.5.1:
- The order of adding the application directory to the Path when using <allfiles> has changed (first the app.dir. and then the rest of the Path).

What's new in v1.5:
- Can now also be used with replaygain programs like mp3gain, wavegain, replaygain (for Musepack), vorbisgain and aacgain. (more info below under "Hints")
- Longer Presets dropdown list (shows max. 15 instead of max. 8 items).
- Simple spell check for the keywords: <infile>, <allfiles> and <outfile.xxx>.

What's new in v1.4:
- It's now possible to run several batch processes simultaneous. In previous versions the go.bat file would get overwritten. But now the batchfiles are numbered (up to 20 and then it starts at 1 again). And they are in their own subdirectory.
- New icon.

What's new in v1.3:
- Removed the Edit button.
- Made the command line presets sort alphabetically.
- Added an 'Always on top' button.

What's new in v1.2:
- Support for XP Visual Styles.
- Tahoma font if OS is Win2000 or higher.
- Replaced the listview with a listbox (because the listview didn't behave well with XP Visual Styles).

What's new in v1.1:
- Add Files dialog remembers last directory. And if that doesn't exist anymore it tries one, two or three directories higher.
- An Edit button. If you hit it, the presets file will be opened in your favourite text editor. The command line combobox reloads the presets file everytime it is clicked, so changes in the presets file are immediately available.

Installation:

- Unzip into a new directory.
- win2dos.exe is not needed when using Windows 2000 or newer.
- The encoders and decoders must be either in the same directory as Batchenc or in the Path. Another posibilty is to specify the location of the encoder on the command line. Example:
"c:\program files\encoders\lame\lame.exe" --alt-preset standard <infile> <outfile.mp3> (the quotes are required when there are spaces in the path). But this last method gets messy soon. I prefer to have all codecs in one directory and add this directory to the search Path. In Windows XP this can be done in: Control Panel -> System -> Advanced -> Environment Variables -> Path -> Edit.
- Run "Batchenc.exe".

If you're in Windows 95/98 and get an error when you try to run the front-end, you probably need to install the Visual Basic 6 Runtime files. Get it here: http://download.microsoft.com/download/5/a/d/5ad868a0-8ecd-4bb0-a882-fe53eb7ef348/VB6.0-KB290887-X86.exe


Usage:

- Drag and drop wave files from Windows Explorer into the Batchenc file list or press the "Add files" button and put files on the list with the "Add Files" dialog.
- Enter the command line you want to use, or select one of the presets. <infile> represents the file on the the list. <outfile.extension> is the base filename of the input file, prepended with the selected output directory and appended with the desired extension.
- Optional: Select an output directory. If the output directory doesn't exist it will automatically be created.
- Hit "Start"
- Note that all that Batchenc does is create and launch a batch file. This is done on the moment you hit the "Start" button. So after that you can safely start the next job or even close Batchenc.

Hints:

- The command line presets are in a file named Batchenc_presets.cfg. This is a normal text file. Presets can be added and removed by hitting the + and the - button.

- To transcode from one compressed format to another pipes can be used if the decoder has standard output and the encoder has standard input (check this in the help of the encoder and decoder you want to use). There's one example in the Batchenc_presets.example file:
flac -dc <infile> | lame --alt-preset standard - <outfile.mp3>
If the decoder doesn't have standard output or the encoder doesn't have standard input you can always use the method with an intermediate wav file. See this example:
ttaenc -d <infile> -o <outfile.wav> && mppenc <outfile.wav> <outfile.mpc> && del <outfile.wav>

- If you want to tag your files directly after encoding without clearing the list of wav files and loading the encoded files, you can use:
tag.exe --auto <outfile.mp3>
Or even easier, you can encode and tag in one run. For example:
lame --preset standard <infile> <outfile.mp3> && tag --auto <outfile.mp3>

- The normal behaviour of Batchenc is to create a new command line for every file on the list. Replaygain programs have to scan all tracks on an album for calculating the album gain. Therefore all files must be on one command line. This can be done by using <allfiles> instead of <infile>. For example:
mp3gain /a <allfiles>
replaygain --auto <allfiles>
All files that are in the same directory will be put on one command line. So if each album is in it's own directory all will go fine. You can put more than one album (directory) on the list. Each album will get it's own command line.
If you just want to apply radio gain then it's safe to use <infile>. For example:
mp3gain /r <infile>

----------------

win2dos is for converting Windows ANSI characters in the batch file to Windows OEM codepage. It is only needed in Win9x. win2dos is made by Case: www.saunalahti.fi/cse/

----------------

Batchenc is based on the source code of vbLamer by Chetan Sarva.

Special thanks to Enrico Palmeri, Chetan Sarva, Case and Volker Jung.

----------------

Batchenc is made by Speek.

Visit my website at: http://members.home.nl/w.speek

Send comments to w.speek@wanadoo.nl
