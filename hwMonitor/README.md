# hwMonitor

## Overview
The hwMonitor project is a lightweight hardware monitoring module developed using ASP.NET Core Minimal API. It serves as a backend for a dashboard web application, providing real-time statistics about the system's hardware components, including CPU, GPU, and RAM.

## Project Structure
The project consists of the following files and directories:

- **Program.cs**: Entry point of the application that initializes the hardware monitoring and sets up the API routes.
- **Models/HardwareStats.cs**: Defines the data model for hardware statistics.
- **Services/IHardwareMonitorService.cs**: Interface for monitoring hardware statistics.
- **Services/HardwareMonitorService.cs**: Implementation of the hardware monitoring service.
- **Visitors/UpdateVisitor.cs**: Class necessary for visiting and updating hardware components.
- **appsettings.json**: Configuration settings for the application.
- **appsettings.Development.json**: Development-specific configuration settings.
- **hwMonitor.csproj**: Project file that includes package references and target framework.

## Setup Instructions
1. **Clone the Repository**: 
   ```bash
   git clone <repository-url>
   cd hwMonitor
   ```

2. **Install Dependencies**: 
   Ensure you have the .NET 8.0 SDK installed. Restore the project dependencies by running:
   ```bash
   dotnet restore
   ```

3. **Run the Application**: 
   To start the application, use the following command:
   ```bash
   dotnet run
   ```
   Note: The application may require Administrator mode to access certain hardware statistics. Make sure to run the terminal or command prompt as an Administrator.

## Usage
Once the application is running, you can access the hardware statistics by navigating to the following endpoint:
```
GET /api/stats
```
This endpoint returns a JSON response containing the current CPU, GPU, and RAM statistics.

## Contributing
Contributions to the hwMonitor project are welcome. Please feel free to submit issues or pull requests for any enhancements or bug fixes.