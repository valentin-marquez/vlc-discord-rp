import os
import struct


class Image:
	"""A minimal class that mimics the PIL.Image.Image interface needed by pystray"""

	def __init__(self, width, height, color=(90, 0, 175)):
		self.width = width
		self.height = height
		self.color = color
		self.mode = "RGB"
		self._data = bytes([color[0], color[1], color[2]] * (width * height))
		self._tempfile = None

	def tobytes(self):
		"""Return raw bytes representing the image (R, G, B for each pixel)"""
		return self._data

	def save(self, fp, format=None):
		"""Save the image to a file or file-like object

		For ICO format, creates a minimal valid ICO file
		"""
		if format == "ICO":
			# Create a valid ICO file structure
			width = self.width
			height = self.height

			# ICO header (6 bytes)
			header = bytes(
				[
					0,
					0,  # Reserved, must be 0
					1,
					0,  # Image type: 1 = ICO
					1,
					0,  # Number of images
				]
			)

			# Directory entry (16 bytes)
			directory = bytes(
				[
					width if width < 256 else 0,  # Width, 0 means 256
					height if height < 256 else 0,  # Height, 0 means 256
					0,  # Color count, 0 for true color
					0,  # Reserved
					1,
					0,  # Color planes
					32,
					0,  # Bits per pixel
					# Size of bitmap data (width * height * 4 bytes for RGBA + 40 bytes for BITMAPINFOHEADER)
					(40 + (width * height * 4)) & 0xFF,
					((40 + (width * height * 4)) >> 8) & 0xFF,
					((40 + (width * height * 4)) >> 16) & 0xFF,
					((40 + (width * height * 4)) >> 24) & 0xFF,
					# Offset to bitmap data (always 22 for one image)
					22,
					0,
					0,
					0,
				]
			)

			# BITMAPINFOHEADER (40 bytes)
			bmp_header = struct.pack(
				"<IIIHHIIIIII",
				40,  # biSize
				width,  # biWidth
				height * 2,  # biHeight (doubled because ICO format requires it)
				1,  # biPlanes
				32,  # biBitCount
				0,  # biCompression
				width * height * 4,  # biSizeImage
				0,  # biXPelsPerMeter
				0,  # biYPelsPerMeter
				0,  # biClrUsed
				0,  # biClrImportant
			)

			# Bitmap data (BGRA format)
			bitmap_data = bytearray()
			r, g, b = self.color
			for y in range(height - 1, -1, -1):  # ICO format stores rows bottom-to-top
				for x in range(width):
					bitmap_data.extend([b, g, r, 255])  # BGRA (alpha = 255)

			# Write everything to the file
			if hasattr(fp, "write"):
				fp.write(header + directory + bmp_header + bitmap_data)
			else:
				with open(fp, "wb") as f:
					f.write(header + directory + bmp_header + bitmap_data)
		else:
			# For other formats, just write RGB data
			if hasattr(fp, "write"):
				fp.write(self._data)
			else:
				with open(fp, "wb") as f:
					f.write(self._data)

	@staticmethod
	def open(path):
		"""Open an image file and return an Image object

		If the file exists, attempts to read its dimensions and first pixel color.
		Falls back to default if unable to read the file.
		"""
		try:
			if not os.path.exists(path):
				return Image(64, 64)

			with open(path, "rb") as f:
				# Try to detect if it's a supported format
				header = f.read(24)  # Read enough bytes for basic detection

				# Basic PNG detection
				if header.startswith(b"\x89PNG\r\n\x1a\n"):
					# Extract width and height from PNG header
					width = int.from_bytes(header[16:20], byteorder="big")
					height = int.from_bytes(header[20:24], byteorder="big")
					# Use a default color since parsing PNG color data is complex
					return Image(width, height)

				# Basic ICO detection
				if header.startswith(b"\x00\x00\x01\x00"):
					# Extract width and height from ICO header
					width = header[6]
					width = 256 if width == 0 else width
					height = header[7]
					height = 256 if height == 0 else height
					return Image(width, height)

				# For unsupported or unrecognized formats, return a default image
				return Image(64, 64)
		except (IOError, OSError):
			# If file doesn't exist or can't be read, return a default image
			return Image(64, 64)

	@staticmethod
	def new(mode, size, color=(90, 0, 175)):
		"""Mock Image.new method that creates a new image with the given parameters"""
		width, height = size if isinstance(size, tuple) else (size, size)
		return Image(width, height, color)
