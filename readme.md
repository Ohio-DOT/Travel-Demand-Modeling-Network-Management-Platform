# 🚦 Travel Demand Modeling Network Management Platform

<img width="4021" height="2268" src="https://raw.githubusercontent.com/Ohio-DOT/Travel-Demand-Modeling-Network-Management-Platform/refs/heads/main/docs/img/net_mgt.png" alt="Screenshot of the Platform's Main Page">
  
**A modern web platform that streamlines how highway networks are maintained for MPO and state-level travel demand modeling.**

---

# 🧭 Overview

This platform supports the lifecycle of travel demand modeling networks, including:

- Uploading and validating **networks and projects**
- Applying and managing **project-level network edits** (“changesets”)
- Detecting conflicts between projects
- Building final scenario networks
- Viewing networks on an interactive web map (vector tiles)
- Exporting networks to standard GIS formats (SHP or GDB)

---

# 🔧 Current Functional Features

### **1. User & Authentication**
- User signup and JWT‑based login
- User profile endpoint with role awareness
- Superuser protections for base network uploads

### **2. Base Network Management**
- Upload `nodes.shp` & `links.shp`  
- Automatic validation and geometry checks  
- Creates a “base” changeset that other edits build upon  

### **3. Changeset & Project Tools**
- Upload *netchange* JSON packages containing create/modify/delete operations  
- Automatic versioning of nodes and links  
- Conflict detection among dependent changesets  
- Dependency tree generation for project networks  
- Automatic creation of netchange files by comparing an edited network vs. base  

### **4. Comparison & Netchange Packaging**
- Spatial + attribute comparison  
- Groups project edits by Project ID (PID)  

### **5. Web Map Tile Services**
- Mapbox Vector Tile (MVT) endpoint for network visualization  
- Zoom-level‑dependent simplification and detail control  
- Tile validation endpoint checks project conflicts before drawing  

### **6. Network Building & Export**
- Combine base + selected projects into a full network  
- Export as:
  - ESRI Shapefile (.shp)
  - ESRI File Geodatabase (.gdb)

---

# 💻 Tech Stack

### **Frontend**
- Node.js 18+
- React  
- Tailwind CSS  
- Mapbox GL / Vector Tiles  

### **Backend**
- Python 3.10+
- Django  
- Django REST Framework  
- PostgreSQL + PostGIS  
- GeoPandas, Shapely, Pyogrio  
- JWT Authentication (SimpleJWT)
