# Solar Panel QC Automation System

## Overview
The **Solar Panel QC Automation System** automates the quality control (QC) process for solar panel inspection reports. In solar manufacturing environments, inspection reports often contain module matrices, serial numbers, electrical measurements, and other important parameters that must be verified before panels are deployed.

Manual verification of these inspection reports is time-consuming, prone to human error, and difficult to scale when dealing with large volumes of solar panel production data.

This project automates the QC workflow by:
- Extracting inspection data using **Optical Character Recognition (OCR)**
- Cleaning and structuring the extracted information
- Applying **rule-based validation checks**
- Cross-verifying values with reference data
- Automatically generating structured **QC reports**

The system improves efficiency, reduces manual effort, and enables scalable verification of solar panel inspection data.

---

## Features

- Automated extraction of inspection data using OCR  
- Data cleaning and preprocessing of extracted values  
- Rule-based quality validation  
- Cross-verification with reference Excel data  
- Batch processing of multiple inspection reports  
- Automatic generation of QC reports in Excel format  
- Modular and scalable architecture  

---

## System Workflow

```
Input Inspection Files
        │
        ▼
Input Handler
        │
        ▼
OCR Engine
        │
        ▼
Data Cleaning
        │
        ▼
Quality Evaluation
        │
        ▼
Cross Verification
        │
        ▼
Report Generation
        │
        ▼
Final QC Output
```

---

## Project Structure

```
solar/
│
├── batch_manager.py
├── cross_verifier.py
├── data_cleaner.py
├── input_handler.py
├── ocr_engine.py
├── quality_evaluator.py
├── report_generator.py
│
├── input/
├── output/
├── logs/
│
└── main.py
```

---

## Module Description

### input_handler.py
Handles incoming inspection files and prepares them for processing.

### batch_manager.py
Manages batch processing of multiple inspection reports and ensures files are processed sequentially.

### ocr_engine.py
Extracts text and numerical values from inspection images using OCR techniques.

### data_cleaner.py
Cleans and structures the extracted OCR data by removing noise and correcting formatting issues.

### quality_evaluator.py
Applies rule-based validation to check correctness and consistency of extracted values.

### cross_verifier.py
Compares extracted values with reference Excel datasets to detect mismatches.

### report_generator.py
Generates final QC reports containing extracted values, validation results, and error flags.

---

## Installation

### Requirements

- Python 3.8 or higher  
- pip  

### Install dependencies

```
pip install -r requirements.txt
```

### Common libraries used

- pandas  
- numpy  
- opencv-python  
- pytesseract  
- openpyxl  

---

## Usage

1. Place inspection files inside the **input** folder.

2. Run the pipeline:

```
python main.py
```

3. The system will automatically:

- Detect input inspection files  
- Extract data using OCR  
- Clean and validate the extracted information  
- Generate QC reports  

4. Final QC reports will be saved in the **output** folder.

---

## Example Output

The generated Excel QC report typically includes:

- Extracted inspection values  
- Validation results  
- Error flags or warnings  
- Final QC status (Pass / Fail / Manual Review)

---

## Advantages

- Reduces manual inspection workload  
- Improves accuracy of QC verification  
- Handles large volumes of inspection data  
- Generates structured and easy-to-analyze reports  

---

## Future Improvements

Possible enhancements for the system include:

- Integration with deep learning based OCR models  
- Real-time monitoring dashboards  
- Cloud-based QC processing pipelines  
- Machine learning based anomaly detection for inspection data  

---

## Applications

- Solar panel manufacturing quality control  
- Automated inspection workflows  
- Renewable energy production monitoring  
- Industrial inspection automation systems  
