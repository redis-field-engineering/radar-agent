# Building enterprise-credentials Executable

This document explains how to build a standalone Linux executable for the `enterprise_credentials.py` script using PyInstaller.

## Overview

The build process creates a single executable file that includes all Python dependencies, allowing users to run the script without installing Python or any additional packages.

## Prerequisites

- Python 3.7 or higher
- pip3
- Linux environment (or WSL on Windows)

## Build Methods

### Method 1: Automated Build (Recommended)

1. Navigate to the build directory:
   ```bash
   cd utilities/agent-provisioning
   ```

2. Run the build script:
   ```bash
   ./build.sh
   ```

3. The executable will be created at `dist/enterprise-credentials`

### Method 2: Manual PyInstaller Build

If you prefer to run PyInstaller manually:

```bash
# Install dependencies
pip3 install -r requirements.txt

# Build executable
pyinstaller --onefile \
    --name enterprise-credentials \
    --hidden-import yaml \
    --hidden-import requests \
    --hidden-import urllib3 \
    enterprise_credentials.py
```

## Build Output

The build process creates:
- `dist/enterprise-credentials` - The standalone executable
- `build/` - Temporary build files (can be deleted)
- `enterprise-credentials.spec` - PyInstaller specification file

## Testing the Executable

After building, test the executable:

```bash
# Test help
./enterprise-credentials --help

# Test version (if implemented)
./enterprise-credentials --version

# Test basic functionality
./dist/enterprise-credentials --endpoint https://localhost:9443 --username admin@re.demo --create
```

## Distribution

The executable can be distributed to any Linux system with the same architecture (typically x86_64). Users can run it directly without installing Python or any dependencies.

### File Size

The executable typically ranges from 15-25 MB, depending on the included dependencies.

### Compatibility

- **Architecture**: x86_64 (AMD64)
- **OS**: Linux (glibc-based distributions)
- **Dependencies**: None (self-contained)

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   chmod +x enterprise-credentials
   ```

2. **Missing Dependencies**
   - Ensure all dependencies are listed in `requirements.txt`
   - Check that `--hidden-import` flags include all required modules

3. **Large File Size**
   - The executable includes all Python dependencies
   - Consider using `--exclude-module` to remove unused modules

4. **Build Failures**
   - Clean previous builds: `rm -rf build/ dist/ __pycache__/`
   - Ensure you have sufficient disk space
   - Check that all source files are present

### Debug Build

For debugging, create a debug build:

```bash
pyinstaller --onefile --debug all enterprise-credentials.py
```

## Advanced Configuration

### Custom Spec File

The `enterprise-credentials.spec` file contains the PyInstaller configuration. You can modify it to:

- Add additional hidden imports
- Include data files
- Configure UPX compression
- Set custom build options

### Optimizing Size

To reduce executable size:

1. Use UPX compression (enabled by default)
2. Exclude unused modules:
   ```bash
   pyinstaller --onefile --exclude-module matplotlib --exclude-module numpy enterprise-credentials.py
   ```

3. Use `--strip` to remove debug symbols (may affect debugging)

## Security Considerations

- The executable contains all source code and dependencies
- Consider code signing for production distributions
- Verify the executable on target systems before deployment

## CI/CD Integration

For automated builds, you can integrate the build process into your CI/CD pipeline:

```yaml
# Example GitHub Actions step
- name: Build executable
  run: |
    cd utilities/agent-provisioning
    ./build.sh
    ls -la dist/enterprise-credentials
```

## Support

For build issues or questions:
1. Check the troubleshooting section above
2. Review PyInstaller documentation
3. Ensure all dependencies are properly specified 