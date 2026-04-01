package com.asvi.breathalyzer;

// represents a single drunk driving record stored in Firebase
public class Record {

    private String licenseNumber;
    private String name;
    private String surname;
    private String vehicleNumber;
    private String email;
    private String location;
    private String timestamp;
    private int    concentration;
    private int    drunkCount;

    public Record() {}

    public Record(String licenseNumber, String name, String surname,
                  String vehicleNumber, String email, String location,
                  String timestamp, int concentration, int drunkCount) {
        this.licenseNumber = licenseNumber;
        this.name          = name;
        this.surname       = surname;
        this.vehicleNumber = vehicleNumber;
        this.email         = email;
        this.location      = location;
        this.timestamp     = timestamp;
        this.concentration = concentration;
        this.drunkCount    = drunkCount;
    }

    public String getLicenseNumber() { return licenseNumber; }
    public String getName()          { return name; }
    public String getSurname()       { return surname; }
    public String getVehicleNumber() { return vehicleNumber; }
    public String getEmail()         { return email; }
    public String getLocation()      { return location; }
    public String getTimestamp()     { return timestamp; }
    public int    getConcentration() { return concentration; }
    public int    getDrunkCount()    { return drunkCount; }

    public void setLicenseNumber(String licenseNumber) { this.licenseNumber = licenseNumber; }
    public void setName(String name)                   { this.name = name; }
    public void setSurname(String surname)             { this.surname = surname; }
    public void setVehicleNumber(String vehicleNumber) { this.vehicleNumber = vehicleNumber; }
    public void setEmail(String email)                 { this.email = email; }
    public void setLocation(String location)           { this.location = location; }
    public void setTimestamp(String timestamp)         { this.timestamp = timestamp; }
    public void setConcentration(int concentration)    { this.concentration = concentration; }
    public void setDrunkCount(int drunkCount)          { this.drunkCount = drunkCount; }
}
