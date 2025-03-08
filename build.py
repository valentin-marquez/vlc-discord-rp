#!/usr/bin/env python3
import argparse
import importlib.util
import os
import platform
import re
import shutil
import subprocess
import sys


def clean():
	"""Clean build artifacts"""
	print("Cleaning build directories...")
	try:
		dirs_to_clean = ["build", "dist", "__pycache__", "release", "VLC_Discord_RP"]

		for dir_name in dirs_to_clean:
			if os.path.exists(dir_name):
				shutil.rmtree(dir_name)

		# Clean .pyc files
		for root, dirs, files in os.walk("."):
			for file in files:
				if file.endswith(".pyc"):
					os.remove(os.path.join(root, file))

		# Remove zip file if it exists
		zip_file = "VLC_Discord_RP.zip"
		if os.path.exists(zip_file):
			os.remove(zip_file)
			print(f"Removed {zip_file}")

		print("Clean completed")
		return True
	except Exception as e:
		print(f"Clean failed: {e}")
		return False


def sign_executable(exe_path, certificate_path, password=None):
	"""Sign an executable with signtool.exe"""
	print(f"Signing executable: {exe_path}")

	if not os.path.exists(exe_path):
		print(f"Error: Executable not found at {exe_path}")
		return False

	# Build signing command
	sign_cmd = [
		"signtool",
		"sign",
		"/f",
		certificate_path,
		"/fd",
		"SHA256",
		"/tr",
		"http://timestamp.digicert.com",
		"/td",
		"SHA256",
	]

	# Add password if provided
	if password:
		sign_cmd.extend(["/p", password])

	sign_cmd.append(exe_path)

	try:
		result = subprocess.run(sign_cmd, capture_output=True, text=True)

		if result.returncode == 0:
			print(f"Successfully signed {exe_path}")
			return True
		else:
			print(f"Signing failed: {result.stderr}")
			return False
	except Exception as e:
		print(f"Error during signing: {e}")
		return False


def build_bootloader():
	"""Build custom PyInstaller bootloader"""
	print("Building custom PyInstaller bootloader...")
	try:
		# Determine the system
		system = platform.system()
		architecture = "64bit" if sys.maxsize > 2**32 else "32bit"

		print(f"Building custom bootloader for {system} {architecture}")

		# Save current directory
		current_dir = os.getcwd()

		# Clone PyInstaller if needed
		if not os.path.exists("pyinstaller_repo"):
			print("Cloning PyInstaller repository...")
			subprocess.run(
				[
					"git",
					"clone",
					"https://github.com/pyinstaller/pyinstaller.git",
					"pyinstaller_repo",
				],
				check=True,
			)

		try:
			# Enter bootloader directory
			os.chdir("pyinstaller_repo/bootloader")

			# Clean any previous builds
			if os.path.exists("build"):
				shutil.rmtree("build")

			# Build the bootloader
			print("Building bootloader...")
			subprocess.run(["python", "./waf", "configure", "all"], check=True)

			# Find the built bootloader files
			bootloader_dir = None
			for root, dirs, files in os.walk("../PyInstaller/bootloader"):
				if system in root:
					bootloader_dir = root
					break

			if not bootloader_dir:
				print("Failed to find built bootloaders")
				return False

			# Check if PyInstaller is installed
			pyinstaller_spec = importlib.util.find_spec("PyInstaller")
			if pyinstaller_spec is None:
				print("\nPyInstaller is not installed. Installing now...")
				try:
					subprocess.run(
						[
							sys.executable,
							"-m",
							"pip",
							"install",
							"git+https://github.com/valentin-marquez/pyinstaller.git",
						],
						check=True,
					)
					# Try again after installation
					pyinstaller_spec = importlib.util.find_spec("PyInstaller")
				except Exception as e:
					print(f"Failed to install PyInstaller: {e}")

			# Find PyInstaller installation path
			pyinstaller_path = None
			if pyinstaller_spec:
				# Get the parent directory of the PyInstaller package
				if pyinstaller_spec.submodule_search_locations:
					pyinstaller_path = pyinstaller_spec.submodule_search_locations[0]

			# If we still can't find it, search in site-packages
			if not pyinstaller_path:
				for path in sys.path:
					if "site-packages" in path and os.path.exists(
						os.path.join(path, "PyInstaller")
					):
						pyinstaller_path = os.path.join(path, "PyInstaller")
						break

			if not pyinstaller_path:
				print("\nWarning: Failed to find PyInstaller installation.")
				print("The bootloaders have been built successfully but were not installed.")
				print(f"Built bootloaders are available at: {os.path.abspath(bootloader_dir)}")
				print("You can manually copy them to your PyInstaller installation when needed.")
				return True  # Return success since bootloaders were built

			# Copy the bootloaders to PyInstaller's installation
			dest_dir = os.path.join(
				pyinstaller_path, "bootloader", os.path.basename(bootloader_dir)
			)
			print(f"\nCopying bootloaders to {dest_dir}")

			if not os.path.exists(dest_dir):
				os.makedirs(dest_dir)

			for file in os.listdir(bootloader_dir):
				if file.startswith("run"):
					shutil.copy2(os.path.join(bootloader_dir, file), dest_dir)

			print("Custom bootloader successfully built and installed!")
			return True
		finally:
			# Always return to original directory
			os.chdir(current_dir)

	except subprocess.CalledProcessError as e:
		print(f"Bootloader build failed with return code: {e.returncode}")
		return False
	except Exception as e:
		print(f"Bootloader build failed: {e}")
		return False


def build_app(version=None, dev=False, uac_level=None, sign_cert=None, sign_pass=None):
	"""Build the VLC Discord RP application executable"""
	print("Building VLC Discord Rich Presence application...")

	# Update version_info.txt if version is provided
	if version:
		update_version_info(version)

	# Update manifest if UAC level is provided
	if uac_level:
		update_manifest("app.manifest", uac_level)

	# Modify app.spec for dev mode if needed
	spec_file_path = os.path.join("spec", "app.spec")
	if dev:
		print("Development mode: Building with console window...")
		# Read the spec file
		with open(spec_file_path, "r") as f:
			spec_content = f.read()

		# Backup original spec file
		with open(f"{spec_file_path}.bak", "w") as f:
			f.write(spec_content)

		# Replace console=False with console=True
		spec_content = spec_content.replace("console=False", "console=True")

		# Write modified spec file
		with open(spec_file_path, "w") as f:
			f.write(spec_content)

	# Run PyInstaller for the main application
	try:
		subprocess.run(["pyinstaller", "--clean", "spec/app.spec"], check=True)
		print("Application build complete!")
		success = os.path.exists(os.path.join("dist", "VLC Discord Presence.exe"))
	except subprocess.CalledProcessError:
		print("Application build failed!")
		success = False

	# Restore original spec file if modified
	if dev and os.path.exists(f"{spec_file_path}.bak"):
		shutil.move(f"{spec_file_path}.bak", spec_file_path)

	# Después de construir la aplicación, firmar si se proporciona certificado
	if success and sign_cert:
		app_path = os.path.join("dist", "VLC Discord Presence.exe")
		sign_executable(app_path, sign_cert, sign_pass)

	return success


def update_version_info(version):
	"""Update version_info.txt with provided version"""
	print(f"Updating version to {version}...")

	# Read the current content
	version_file_path = os.path.join("spec", "version_info.txt")
	with open(version_file_path, "r") as f:
		content = f.read()

	# Split version into components
	version_parts = version.split(".")
	while len(version_parts) < 3:
		version_parts.append("0")
	version_tuple = ", ".join(version_parts) + ", 0"

	# Replace version strings
	content = re.sub(r"filevers=\(\d+, \d+, \d+, \d+\)", f"filevers=({version_tuple})", content)
	content = re.sub(r"prodvers=\(\d+, \d+, \d+, \d+\)", f"prodvers=({version_tuple})", content)
	content = re.sub(r"u'FileVersion', u'\d+\.\d+\.\d+'", f"u'FileVersion', u'{version}'", content)
	content = re.sub(
		r"u'ProductVersion', u'\d+\.\d+\.\d+'",
		f"u'ProductVersion', u'{version}'",
		content,
	)

	# Write the updated content
	with open(version_file_path, "w") as f:
		f.write(content)


def update_manifest(manifest_file, uac_level):
	"""Update manifest file with the specified UAC level"""
	print(f"Updating manifest with UAC level: {uac_level}")

	manifest_path = os.path.join("spec", manifest_file)
	if not os.path.exists(manifest_path):
		print(f"Warning: Manifest file {manifest_path} not found. Creating it...")
		create_default_manifest(manifest_path, uac_level)
		return

	with open(manifest_path, "r") as f:
		content = f.read()

	# Replace the requestedExecutionLevel
	content = re.sub(
		r'<requestedExecutionLevel level="[^"]*"',
		f'<requestedExecutionLevel level="{uac_level}"',
		content,
	)

	with open(manifest_path, "w") as f:
		f.write(content)


def create_default_manifest(manifest_path, uac_level):
	"""Create a default manifest file with the specified UAC level"""
	manifest_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity type="win32" name="VLCDiscordPresence" version="1.0.0.0" processorArchitecture="*"/>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="{uac_level}" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <supportedOS Id="{{e2011457-1546-43c5-a5fe-008deee3d3f0}}"/>
      <supportedOS Id="{{35138b9a-5d96-4fbd-8e2d-a2440225f93a}}"/>
      <supportedOS Id="{{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}}"/>
      <supportedOS Id="{{1f676c76-80e1-4239-95bb-83d0f6d0da78}}"/>
      <supportedOS Id="{{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}}"/>
    </application>
  </compatibility>
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <longPathAware xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">true</longPathAware>
    </windowsSettings>
  </application>
</assembly>"""

	os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
	with open(manifest_path, "w") as f:
		f.write(manifest_content)


def build_installer(uac_level=None, sign_cert=None, sign_pass=None):
	"""Build the installer executable"""
	print("Building installer...")

	# Update manifest if UAC level is provided
	if uac_level:
		update_manifest("installer.manifest", uac_level)

	try:
		# First make sure the application was built - note the updated path
		app_path = os.path.join("dist", "VLC Discord Presence.exe")
		if not os.path.exists(app_path):
			print(f"Error: Application executable not found at {app_path}. Run build first.")
			return False

		# Run PyInstaller for the installer using the spec file
		print("Running PyInstaller with spec/installer.spec...")
		result = subprocess.run(
			["pyinstaller", "--clean", "spec/installer.spec"],
			check=True,
			capture_output=True,
			text=True,
		)
		print("PyInstaller output:")
		print(result.stdout)

		if result.stderr:
			print("PyInstaller errors:")
			print(result.stderr)

		installer_path = os.path.join("dist", "VLC Discord RP Setup.exe")
		success = os.path.exists(installer_path)
		if success:
			print(f"Installer created successfully at {installer_path}")
		else:
			print(f"Installer not found at expected location {installer_path}")

		# Después de construir el instalador, firmar si se proporciona certificado
		if success and sign_cert:
			sign_executable(installer_path, sign_cert, sign_pass)

		return success

	except subprocess.CalledProcessError as e:
		print(f"Installer build failed with return code: {e.returncode}")
		print("Output:", e.stdout)
		print("Error:", e.stderr)
		return False
	except Exception as e:
		print(f"Installer build failed: {e}")
		return False


def package():
	"""Package everything into a release zip"""
	print("Creating release package...")
	try:
		# Create release directory
		release_dir = "release"
		if os.path.exists(release_dir):
			shutil.rmtree(release_dir)
		os.makedirs(release_dir)

		# Copy installer
		installer_path = os.path.join("dist", "VLC Discord RP Setup.exe")
		if os.path.exists(installer_path):
			shutil.copy2(installer_path, os.path.join(release_dir, "VLC Discord RP Setup.exe"))
		else:
			print("Warning: Installer executable not found.")
			return False

		# Copy readme, license and changelog
		for file in ["README.md", "LICENSE", "CHANGELOG.md"]:
			if os.path.exists(file):
				shutil.copy2(file, os.path.join(release_dir, file))

		# Create ZIP archive
		shutil.make_archive("VLC_Discord_RP", "zip", release_dir)
		print("Release package created: VLC_Discord_RP.zip")
		return os.path.exists("VLC_Discord_RP.zip")
	except Exception as e:
		print(f"Package creation failed: {e}")
		return False


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Build VLC Discord Rich Presence")
	parser.add_argument(
		"command",
		choices=["clean", "build", "installer", "package", "all", "bootloader"],
		help="Build command to run",
	)
	parser.add_argument(
		"--version",
		help="Version number to update in version_info.txt",
	)
	parser.add_argument(
		"--dev",
		action="store_true",
		help="Build in development mode with console window enabled",
	)
	parser.add_argument(
		"--app-uac",
		choices=["asInvoker", "highestAvailable", "requireAdministrator"],
		default="asInvoker",
		help="UAC execution level for the main application",
	)
	parser.add_argument(
		"--installer-uac",
		choices=["asInvoker", "highestAvailable", "requireAdministrator"],
		default="requireAdministrator",
		help="UAC execution level for the installer",
	)
	parser.add_argument(
		"--sign-cert",
		help="Path to the code signing certificate (.pfx file)",
	)
	parser.add_argument(
		"--sign-pass",
		help="Password for the code signing certificate",
	)

	args = parser.parse_args()

	if args.command == "clean":
		clean()
	elif args.command == "build":
		build_app(
			version=args.version,
			dev=args.dev,
			uac_level=args.app_uac,
			sign_cert=args.sign_cert,
			sign_pass=args.sign_pass,
		)
	elif args.command == "installer":
		build_installer(
			uac_level=args.installer_uac, sign_cert=args.sign_cert, sign_pass=args.sign_pass
		)
	elif args.command == "package":
		success = package()
		if not success:
			exit(1)
	elif args.command == "bootloader":
		success = build_bootloader()
		if not success:
			exit(1)
	elif args.command == "all":
		if not clean():
			exit(1)
		if not build_bootloader():
			exit(1)
		if not build_app(
			args.version,
			dev=args.dev,
			uac_level=args.app_uac,
			sign_cert=args.sign_cert,
			sign_pass=args.sign_pass,
		):
			exit(1)
		if not build_installer(
			uac_level=args.installer_uac, sign_cert=args.sign_cert, sign_pass=args.sign_pass
		):
			exit(1)
		if not package():
			exit(1)
	else:
		parser.print_help()
