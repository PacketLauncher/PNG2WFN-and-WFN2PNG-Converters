PNGtoWFN and WFNtoPNG converters, by Gal Shemesh (PacketLauncher)
https://github.com/PacketLauncher/PNG2WFN-and-WFN2PNG-Converters
-----------------------------------------------------------------
These Python script can convert a PNG file into an Adventure Game Studio (AGS) engine WFN font format and vice versa.

Each can be used by dragging the relevant file(s) over it, or from the CLI.

- The PNGtoWFN doesn't have any special settings in the CLI and behaves the same as dragging files over it. See below to learn about 4-bit shading and how to prepare a PNG for a WFN conversion.

	The CLI syntax is: WFNtoPNG.exe [filename.wfn]
	
- The WFNtoPNG uses default settings when dragging files over it, where in the CLI you can customize them. The defaults are:
	1. Glyphs per row: 16
	2. Glyphs layout: original size
	3. Separator color: magenta (FF00FF)
	4. Export placeholders: false (skipping placeholders and creating multiple files of actual glyphs with specified range, such as 'MyFont_0-127.png' and 'MyFont_1488-1514' if there's a gap of placeholders between index 127 and 1488).
	5. Placeholder dimensions: 8x9 pixels
	
	The CLI command syntax is: WFNtoPNG.exe "MyFont.wfn" [glyphs per row] [glyph layout | original or fixed] [separator color | hex/RGB number or -1 for transparency] [optional: export placeholders bool | 1 or true] [optional: placeholder dimensions | 8x9]
	
	Examples:
	
	WFNtoPNG.exe "MyFont.wfn" 16 original FF00FF
		- This will make a 16 glyphs per row in their original glyphs size and magenta separator, skip any placeholders and generate multiple PNG files, just like when dragging files over the EXE.
	
	WFNtoPNG.exe "MyFont.wfn" 16 original 255,85,255 true
		- This does the same as the above, only that the separator color number is passed as RGB, convert all placeholders to blank glyphs at the default size of 8x9 pixels (since no dimensions are passed), and generate a single continues file with a range of up to the last glyph index that contains data in it, such as 'MyFont0-65535.png' (better to avoid unless you really need to).
	
	WFNtoPNG.exe "MyFont.wfn" 20 fixed -1 1 5x5
		- This will make a 20 glyphs per row in a fixed size, with transparent separator, and placeholders as blank at the size of 5x5 pixels (note that fixed size will add black pixels from the right and bottom of any narrow/short glyphs to make them align correctly amongst the other glyphs - better to avoid and use 'original' instead if you wish to preserve your original glyphs dimensions. Also note that in this example, the 'true' for exporting placeholders is passed as the integer '1' - use what suits you best).

A note about 4-bit shading:
---------------------------
The original WFN format is a 1-bit font, meaning that it can contain only Black and White pixels; the AGS Editor/Engine considers black as transparent and white as the font color, which changes to the text color that you set for it.

The extended 4-bit WFN format supports shadings to make the font look less flat and more elegant (supported from AGS 4.x and above only!). It uses the following 4-bit grayscale shadings table, which in the AGS Editor/Engine are converted to the closest color match of their parallel brightness values when compared to it. That means, if the source WFN font has pixel shading and you set it in AGS to Red, each grayscale shade will be drawn in that parallel brightness of Red.

Level	Hex			RGB
0		#000000		0, 0, 0				<-- this black represents transparency
1		#111111		17, 17, 17
2		#222222		34, 34, 34
3		#333333		51, 51, 51
4		#444444		68, 68, 68
5		#555555		85, 85, 85
6		#666666		102, 102, 102
7		#777777		119, 119, 119
8		#888888		136, 136, 136
9		#999999		153, 153, 153
10		#AAAAAA		170, 170, 170
11		#BBBBBB		187, 187, 187
12		#CCCCCC		204, 204, 204
13		#DDDDDD		221, 221, 221
14		#EEEEEE		238, 238, 238
15		#FFFFFF		255, 255, 255		<-- this white represents the font color
	
When converting a PNG to WFN, it will automatically check if there are shading on the glyphs. If it doesn't find any shadings, that means that you only used Black and White when drawing it, and it will generate a 1-bit WFN file that is backward compatible with any previous version of AGS. Else, it will generate a 4-bit WFN file that is supported in AGS 4.x and above only!

Rules for preparing a PNG for a WFN conversion:
-----------------------------------------------
Converting a PNG to WFN is straight forward and would create a WFN file out of the glyphs in the PNG file. For this to work, the first glyph should be drawn from the Top-left of the image and to the right. Each glyph must have a separator border from its right and bottom edges, even if it's a single glyph. You can draw your glyphs in a long stright line or in rows; the program will automatically check if there are more glyphs on a new row when it reaches the right edge of the image. For the separator color, it is best to use a different color than the above table, such as magenta (#FF00FF) or transparency.

Use Black (#000000) and White (#FFFFFF) to draw your font. If you're aiming for a font with shading, you may use the grayscale shading from the above table; in my 1.1.0.0 version for Rulaman's WFN FontEditor you'd have a pre-configured palette to pick the colors from. If you happen to draw your font in an external paint program and used different shadings values, their colors will be compared versus the above 4-bit grayscale table and converted to the closest shade from it.

In fonts in general, each character must be positioned in its predefined index in either the ASCII / ASNI / Unicode tables for it to be shown correcly when the text is rendered to the screen. For example, the English alphabet index range is 65-90 for the capital letters and 97-122 for the lowercase letters. Numbers index range is 48-57. And there are other universal signs, symbols and foreign languages characters in other ranges. Refer to the ASCII / ASNI / Unicode tables on the internet to learn more about the index position of each character.

So if you wish to create a PNG that contains only numbers and the English Alphabet, you'd need to tell the converter in which index to put these glyphs. If you don't, it will start importing them from index 0. To doing so, we can either draw empty blank (black) glyphs that represet each character index and have them all on a single PNG file, which works but this will be difficult to track which index is which and to much work to make, or that we could use a special syntax in the PNG filename, and the converter will automatically detect that. For example:

	Let's say we want to make a font that covers the 0-9 numbers (indexes 48-57), and the full English alphabet (indexes 65-90 and 97-122). We can draw the 0-9 glyphs on one PNG and save it as 'MyFont_48-57.png'. When converting it to WFN, the program will recotgnize the range syntax after the filename and know that these glyphs should be positioned in the WFN file from index 48 to index 57.
	
	For the capital English glyphs, we'll do the same but save the file as 'MyFont_65-90.png', and for the lowercase glyphs we'll save the file as 'MyFont_91-122.png'.
	
	You can basically drag multiple files over the EXE, but the neat part is that you don't have to - all you have to do is to drag only one of them on the EXE, and the convertor will detects if the same folder contains multiple files that share the same filename before the range syntax starts, in which case it will use them all when generating the WFN file.
	
	If you want to make changes to your glyphs, all you have to do is to edit the relevant PNG and to re-drag it over the EXE and it will re-generate the WFN font, overwriting an existing one.
	
	* In any case that you don't specify a range after the filename, the glyphs will be imported from index 0.


Making an EXE from the source Python scripts:
---------------------------------------------
* This is for developers who wish to make adjustments to the source scripts for generating an EXE out of them.

1. Install Python.

2. Open CMD and install the both pyinstaller and pillow library:
	py -m pip install pillow
	py -m pip install pyinstaller
	
3. Run the following to build an EXE:
	py -m PyInstaller --onefile --console --clean --icon="PNG2WFN.ico" --name PNG2WFN PNG2WFN.py
	py -m PyInstaller --onefile --console --clean --icon="WFN2PNG.ico" --name WFN2PNG WFN2PNG.py
	