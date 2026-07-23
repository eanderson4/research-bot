# Dense Factual Notes

**Source:** arXiv preprint, Accepted Manuscript of article in *International Journal of Remote Sensing*, published 03 Dec 2025.  
**Title:** “Towards autonomous photogrammetric forest inventory using a lightweight under-canopy robotic drone”  
**Authors:** Väinö Karjalainen∗, Niko Koivumäki∗ (equal contribution), Teemu Hakala, Jesse Muhojoki, Eric Hyyppä, Anand George, Juha Suomalainen, Eija Honkavaara – all from Finnish Geospatial Research Institute FGI, National Land Survey of Finland.  
**Contact:** Väinö Karjalainen, vaino.karjalainen@nls.fi, Vuorimiehentie 5, FI-02150 Espoo, Finland.  
**DOI of final version:** 10.1080/01431161.2025.2579803  
**Date of field tests:** 18 October 2023 (Evo flights) and 26 January 2024 (Paloheinä loop‑closure walk).  

---

## Study Objectives & Novelty
- First empirical validation of a **miniaturized, autonomous, camera‑based robotic drone** for under‑canopy forest reconstruction.
- Research questions:  
  1. What level of autonomous flight reliability can be achieved in challenging boreal forests with current camera‑based navigation methods?  
  2. What DBH estimation accuracy can be achieved with the low‑cost onboard stereo camera data?  
  3. What are the remaining bottlenecks for large‑scale autonomous photogrammetric forest data collection?
- Contributions listed explicitly:  
  • Build and development of a lightweight robotic drone prototype using open‑source methods.  
  • Combining autonomous under‑canopy flight with SfM‑MVS photogrammetry from a low‑cost stereo camera.  
  • DBH validation and analysis of influencing factors.  
  • Comprehensive discussion of limitations and further research directions.

---

## Hardware Prototype
- **Drone frame:** 330 mm quadcopter; propellers with two 6 cm blades each.
- **Weight:** 791 g without batteries, **1153 g with batteries**.
- **Onboard computer:** NVIDIA Jetson Orin NX.
- **Flight controller:** Holybro Kakute H7 (PX4 autopilot compatible), contains IMU.
- **Camera:** Intel RealSense D435, forward‑facing, configured to **1280 × 720 resolution, 30 Hz**; stereo images downsampled to **640 × 360** for VIO. Infrared emitter disabled (sunlight interference).
- **Communication:** ROS (Robot Operating System), MAVROS for onboard computer ↔ autopilot.
- **Calibration:** Kalibr toolbox with Aprilgrid target; IMU noise parameters from Allan Variance ROS, multiplied by 10 before calibration.
- **Cost and weight advantage:** Camera‑based system lighter, cheaper and lower power than LiDAR‑based alternatives (e.g., Ouster OS1).

---

## Autonomous Navigation Stack

### Obstacle Avoidance & Planning
- **Algorithm:** EGO‑Planner‑v2 (Zhou et al. 2022, open‑source GitHub: EGO‑Planner‑code), modified for single drone.
- **Mapping:** 3D occupancy grid maps from depth images; fixed‑size circular buffers; virtual floor/ceiling fixed at beginning of flight (limits altitude changes).
- **Trajectory optimisation:** MINCO trajectory representation; A* global search; penalty terms for smoothness, flight time, dynamical feasibility, obstacle avoidance, uniform evaluation points. Collision‑check continuously running; if imminent collision, emergency stop + replanning.
- **Tracking:** Open‑source controller px4ctrl (Zhejiang University), sends attitude/thrust commands to PX4.

### Visual‑Inertial Odometry (VIO)
- **Algorithm:** VINS‑Fusion (Qin et al. 2018, 2019).
- **Features:** Shi‑Tomasi corner features (max **150**), min distance between features **40 px**, tracked with KLT; RANSAC threshold **1 px**; sliding window optimisation; keyframe selection by parallax (**10 px** threshold); loop detection with BRIEF descriptors and DBoW2.
- **IMU noise parameters set higher than calibration:** accelerometer noise SD 0.2, gyro noise SD 0.05, random walk SDs 0.002/0.0005.  
- **Time offset (td) between camera and IMU:** Kalibr gave fixed value; online estimation also tested. Online estimation yielded slightly more accurate trajectories.
- **Loop closure tests (Paloheinä) without artificial targets:** VINS‑Fusion detected loop closures in homogeneous spruce forest (2000 trees/ha). Increasing feature density (min distance 40→35→30 px) increased loop closures (20→52→82 on short path), but real‑time impact not tested.
- **No GNSS used:** drone entirely reliant on VIO; swarm UWB drift correction omitted.

---

## Test Sites
- **Evo, Finland (61.19°N, 25.11°E):** Two well‑documented sample plots used in many prior studies.
  - *Evo‑medium*: density **650 trees/ha**, mean DBH **28 cm**, species: 81.2 % Norway spruce, 9.4 % Scots pine. Classified “medium” difficulty.
  - *Evo‑difficult*: density **2000 trees/ha**, mean DBH **17 cm**, species: 64.4 % Norway spruce, 18.3 % aspen. Classified “difficult”.
- **Paloheinä, Finland (60.26°N, 24.92°E):** Spruce forest, ~2000 trees/ha, used only for loop‑closure tests (walking with drone).
- **Reference data:** Circular GCPs (diameter 24.7 cm, centre dot 7 cm) placed in plots; relative distances measured with **Leica Nova TS60 total station** (precision ~2 mm).

---

## Flight Tests (Evo, 18 Oct 2023)
- **Mission parameters:** Goal points 34–42 m ahead; max height 2.25–2.75 m above takeoff; target velocity **1 m/s**.
- **Evo‑medium:** 7 flights; two different takeoff locations. **Success rate:** 7/7 (100%). **Smooth trajectories:** 5/7 (71.4%). Emergency stops caused by late detection of thin dry spruce branches.
- **Evo‑difficult:** 9 flights; takeoff heading changed after 6 flights. **Success rate:** 8/9 (87.5%). **Smooth trajectories:** 0/9 (all had at least one emergency stop). One failure due to collision with a thin low branch; others continued after replanning.
- **Table 3 summarised:** Medium forest: 100% success, 71% smooth; Difficult forest: 87.5% success, 0% smooth.
- **VIO ATE (absolute trajectory error) computed for 5 Evo‑medium flights and 3 Evo‑difficult flights (those overlapping GCPs).**
  - **Fixed td:** average ATEpos 0.50 m (sd 0.06) in medium; 0.34 m (sd 0.07) in difficult.
  - **Online td:** average ATEpos 0.47 m (sd 0.02) in medium; 0.33 m (sd 0.04) in difficult.
  - VINS‑Fusion systematically underestimated flight distance (scale error likely from calibration).
- **Example image** shows stable feature tracking even when dry leaves were blown by propellers.

---

## Photogrammetric Processing & 3D Reconstruction
- **Software:** Agisoft Metashape. Every 6th stereo pair used; stereo baseline 5 cm; processing accuracy ±0.0015 m.
- **Image alignment:** 40 000 key points, 4 000 tie points/image; quality high (half resolution); gradual selection outliers removed; bundle adjustment with IOP/EOP optimisation.
- **Point cloud generation:** Highest quality, mild depth filtering.
- **Datasets in Evo‑medium:**  
  - I–IV: individual flights; **Combined:** all four flights merged.  
  - I with 0, 1, 2, 3 GCPs to test impact.
- **Reprojection errors:** 0.29–0.39 pixels.
- **Ground Sampling Distance (GSD):** 4.08–6.17 mm at ground; 0.85–12.34 mm on objects.
- **Point densities per flight:** 2.63–3.58 points/cm²; combined: 8.53 points/cm².
- **Check point RMSE (3 GCPs):** 2D 1.41 cm, 3D 1.48 cm.  
  - **0 GCPs:** 2D 11.36 cm, 3D 11.37 cm.  
  - **1 GCP at start:** 2D 11.72 cm, 3D 11.73 cm.  
  - **2 GCPs (start & end):** 2D 5.26 cm, 3D 5.48 cm.  
  - Camera location RMSE without GCPs: ~11.5 cm.

---

## Tree Detection & DBH Estimation

### Stem Detection Algorithm
- Based on Hyyppä et al. (2020a, 2020c): point cloud segmented vertically (40 cm) and temporally (5 s); clusters from DBSCAN; circle fitting with heuristics (min 35 points, ≥80% points within 30 mm of arc, radius 4–40 cm, central angle ≥60°); stem grouping and PCA for growth direction; final DBH at 1.3 m by smoothing spline.

### Completeness (Evo‑medium)
- **Per flight:** 61.29 % to 79.31 % of reference trees found inside point cloud boundary.
- **Across four flights:** 29 of 33 unique reference trees found (87.88 % completeness).
- **All flights merged:** dropped to 33.33 % (12/36 trees) due to alignment challenges.
- **Best detection with GCPs:** 3 GCPs gave 79.31 %; 0 GCPs gave 72.41 %.
- Some large trees missed despite good reconstruction; poorly reconstructed trees were far from trajectory or occluded.

### DBH Accuracy (Evo‑medium)
- **All trees, per flight:** RMSE **3.33 – 3.97 cm** (10.69 % – 12.98 %), bias –0.67 to +1.40 cm (–2.11 % to +4.71 %).
- **Trees with DBH < 30 cm:** RMSE **1.16 – 2.56 cm** (5.74 % – 12.47 %), bias –0.01 to +0.62 cm (–0.06 % to +3.14 %).
- **Trees with DBH > 30 cm:** RMSE 4.04 – 11.08 cm (8.99 % – 25.44 %).
- Combined flights gave RMSE 2.91 cm (9.14 %) for all trees but only 12 matched trees.
- **GCP impact on RMSE:** Without GCPs, RMSE 4.37 cm (14.66 %); with 3 GCPs, RMSE 3.93 cm (13.68 %). Improvement modest, suggesting potential for GCP‑free processing.
- **No significant correlation** found between camera‑tree distance and DBH error.
- **Reference TLS:** collected April 2020 (4 growth seasons earlier), DBH error <1 cm; tree growth not accounted for, likely contributes to bias.
- **Comparison to literature:** Camera‑based drone SfM studies (Kuželka 2018, Krisanski 2020, He 2025) had similar RMSE ranges; LiDAR mini‑drone studies (Cheng 2024, Liang 2024) achieved 1.5–9.8 cm RMSE under autonomous flight but with heavier/costlier sensors. Heaviest survey‑grade LiDAR under manual control achieved sub‑cm RMSE but in sparser forests.

---

## Identified Bottlenecks & Future Work
- **Thin branch detection:** dry spruce branches caused emergency stops and one crash; alternative cameras or image super‑resolution needed.
- **Blind sides:** 360° FOV (e.g., 360° camera or multi‑camera) or historical occupancy map retention.
- **Altitude constraints:** virtual floor/ceiling fixed relative to takeoff; must be dynamic to adapt to terrain for DBH‑height imaging.
- **Drift compensation:** loop‑closure promising; future should test block/lawmower patterns. GNSS fusion when canopy is thin (e.g., GVINS) could help.
- **Post‑processing already compensates well:** 11 cm 3D error without GCPs vs 50 cm real‑time error, so drift less critical for offline applications.
- **Area coverage:** Straight flight lines insufficient; need waypoint generation or exploration algorithms (e.g., FUEL, RACER, swarm approaches) to image tree trunks from multiple sides. Multi‑view reconstruction expected to reduce large‑diameter tree errors.
- **Additional sensors:** Upward‑facing camera for full stem reconstruction; real‑time point clouds (RealSense) and on‑board object detection (e.g., YOLO) could enable live analysis.
- **Alternate environments:** Tests needed in sparser forests.

---

## Key Organisations & Software
- **Finnish Geospatial Research Institute FGI**, National Land Survey of Finland (authors’ affiliation).
- **International Journal of Remote Sensing** (publisher).
- **EGO‑Planner‑v2** (https://github.com/ZJU-FAST-Lab/EGO-Planner-v2) – MIT‑licensed open‑source planner.
- **VINS‑Fusion** (Qin et al., 2018/2019) – visual‑inertial SLAM.
- **PX4 autopilot**, MAVROS, ROS.
- **Kalibr** camera‑IMU calibration toolbox.
- **Agisoft Metashape** – commercial photogrammetry software.
- **Intel RealSense D435** – stereo‑depth camera.
- **Deep Forestry** (Uppsala, Sweden) and **Emesent Hovermap** with Velodyne VLP‑16 – commercial drone LiDAR systems mentioned in related work.
- **Leica Nova TS60** total station for GCP measurement.
- **Research Council of Finland** grants: 357380, 346710, 357908 (UNITE flagship).

---

## Notes on Staleness & Verifiability
- The final article was published **03 Dec 2025**; technology described (hardware, algorithms) from 2023–2024, still relevant at time of publication.  
- Results are based on a limited number of flights (16 total) in specific boreal plots; generalisation requires further testing.  
- Data availability: “part of the data… available from the corresponding author upon reasonable request.”  
- No commercial interest declared; authors used free grammar/style tools (Grammarly, Writefull) during writing, manually reviewed.

---

RELEVANT LEADS:
- Finnish Geospatial Research Institute FGI (National Land Survey of Finland) – contact vaino.karjalainen@nls.fi for data inquiries.
- EGO‑Planner‑v2 GitHub repository (https://github.com/ZJU-FAST-Lab/EGO-Planner-v2) – open‑source drone navigation.
- VINS‑Fusion and GVINS (GNSS‑VIO fusion) – open‑source SLAM frameworks.
- PX4 autopilot and ROS – widely used drone software ecosystem.
- Agisoft Metashape – commercial photogrammetry suite.
- Intel RealSense D435 – low‑cost stereo‑depth camera.
- Deep Forestry (Uppsala, Sweden) and Emesent Hovermap – LiDAR‑based under‑canopy drone systems.
- Ouster OS1 3D LiDAR (mentioned as alternative sensor).
- Research Council of Finland projects: “Learning techniques for autonomous drone based hyperspectral analysis of forest vegetation” (357380), Fireman (346710), UNITE flagship (357908).
- Evo test site – repeatedly used in LiDAR/SfM forest studies (e.g., Hyyppä et al. 2020a, 2020c; Liang et al. 2018, 2019).  
- DBH estimation algorithm by Hyyppä et al. (2020a, 2020c) – temporal segmentation for drone point clouds.  
- Article DOI: 10.1080/01431161.2025.2579803 – the published version may include supplementary material.