# **Smart Sentry: Real-Time, Phase-Aware Anomaly Detection**

A real-time anomaly detection system for industrial assets, developed for the Baker Hughes Hackathon 2025\. This project addresses the challenge of accurately detecting failures while minimizing false positives during transient operational phases like startup and shutdown.

\<\!-- It is highly recommended to take a screenshot of your running dashboard, upload it to a site like imgur.com, and paste the direct image link here. \--\>

\<\!-- Example: \--\>

## **1\. Project Overview**

**Smart Sentry** solves a critical problem in predictive maintenance: standard monitoring systems often generate false alarms by misinterpreting the normal, volatile behavior of assets during **startup and shutdown phases**.

Our solution is a "phase-aware" system that first identifies an asset's current operational state (STARTUP, STEADY-STATE, or SHUTDOWN) and then uses a specialized machine learning model to detect only genuine anomalies. The system was developed using the **NASA Turbofan Engine Degradation Simulation Dataset (CMAPSS)**.

### **Key Features**

* **Phase-Aware Classification**: Implemented a robust rule-based algorithm using sensor volatility and trends to accurately distinguish between the three core operational phases.  
* **High-Performance Anomaly Detection**: Utilized a supervised RandomForestClassifier trained on a balanced dataset (using SMOTE) to achieve high accuracy and recall.  
* **Proven Performance**: The final model successfully identifies **78% of all true anomalies** while maintaining a **66% precision rate**, fulfilling the evaluation criteria of high accuracy and low false positives.  
* **Real-Time Data Pipeline**: Built an end-to-end streaming architecture capable of ingesting and processing data with low latency.  
* **Interactive Dashboard**: Developed a Streamlit frontend for real-time visualization, control, and alerting.

## **2\. System Architecture**

The project is built on a modern, scalable, and decoupled architecture that uses a producer-consumer pattern to handle real-time data streams.

\[Data Producer\] \-\> \[Kafka Topic\] \-\> \[ML Consumer\] \--+--\> \[Redis Channel\] \-\> \[Streamlit UI\]  
      (producer.py)      |         (consumer\_app.py) |  
                         |                           \+--\> \[PostgreSQL DB\]  
                         |  
                 (NASA Dataset)

* **Producer**: A Python script (producer.py) reads the NASA dataset and streams it to a Kafka topic, simulating a live data feed from an industrial asset.  
* **Kafka**: Acts as a high-throughput, fault-tolerant message bus for the data stream.  
* **Consumer**: A Python application (consumer\_app.py) subscribes to the Kafka topic. It runs the phase classification and anomaly detection models on the incoming data.  
* **Redis**: The consumer publishes the final JSON predictions to a Redis channel, which acts as a high-speed, in-memory message broker for the frontend, ensuring instant UI updates.  
* **PostgreSQL**: For persistence and auditing, all predictions and system metrics (like throughput) are logged to a PostgreSQL database.  
* **Streamlit**: The frontend dashboard (my\_dashboard/app.py) subscribes to the Redis channel to provide a real-time user interface for operators.

## **3\. Final Model Performance**

The RandomForestClassifier was selected as the final model due to its superior balance between precision and recall.

| Metric (Anomaly Class) | Score |
| :---- | :---- |
| **Precision** | 0.66 |
| **Recall** | 0.78 |
| **F1-Score** | **0.71** |

## **4\. Setup Instructions**

### **Prerequisites**

* [Git](https://git-scm.com/downloads)  
* [Docker Desktop](https://www.docker.com/products/docker-desktop/)  
* Python 3.10+

### **Installation**

1. **Clone the Repository**  
   git clone \<your-repository-url\>  
   cd \<your-repository-name\>

2. Create a data directory  
   In the BakerHughesHackathon directory at theroot of the project folder, create a new folder named data.  
   cd BakerHughesHackathon
   mkdir data

3. **Download the Dataset**  
   * Go to the [**NASA Prognostics Center of Excellence Data Repository**](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/).  
   * Find the **"Turbofan Engine Degradation Simulation Data Set"** and download the zip file (CMAPSSData.zip).  
   * Unzip the file. Inside, you will find several text files.  
   * Copy the following three files into the data/ directory you just created:  
     * train\_FD001.txt  
     * test\_FD001.txt  
     * RUL\_FD001.txt  
4. **Create a Python Virtual Environment**  
   \# For Windows  
   python \-m venv venv  
   .\\venv\\Scripts\\activate

   \# For macOS/Linux  
   python3 \-m venv venv  
   source venv/bin/activate

5. Create a requirements.txt file  
   In the root of the project, create a file named requirements.txt and add the following content:  
   pandas  
   scikit-learn  
   joblib  
   numpy  
   kafka-python  
   psycopg2-binary  
   redis  
   streamlit  
   xgboost  
   seaborn  
   matplotlib  
   imbalanced-learn

6. **Install Dependencies**  
   pip install \-r requirements.txt

## **5\. How to Run the Project**

To run the complete application, you will need to open **four separate terminals** in your project's root directory. Make sure your virtual environment is activated in each one.

Step 1: Start the Infrastructure  
In your first terminal, start the Kafka, PostgreSQL, and Redis services using Docker.  
docker-compose up \-d

Wait about a minute for all services to initialize.

Step 2: Start the Backend Consumer  
In your second terminal, start the machine learning consumer script. This will connect to the services and wait for data.  
python consumer\_app.py

You should see messages confirming connections to the database, Redis, and Kafka.

Step 3: Start the Frontend Dashboard  
In your third terminal, navigate to the dashboard folder and run the Streamlit app.  
cd my\_dashboard  
streamlit run app.py

A new tab should open in your web browser with the dashboard. It will be waiting for data.

Step 4: Start the Data Stream  
In your fourth terminal, run the producer script to begin streaming the NASA dataset.  
python producer.py

You can now watch the dashboard in your browser update in real time as the data is processed.