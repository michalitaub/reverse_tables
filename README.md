# ♿ Reverse Tables for Accessibility (PDF Accessibility Tool)

## 🌟 Project Overview

As an accessibility specialist, I frequently encountered a critical challenge: **tables within PDF documents often have an incorrect reading order for screen readers**, especially when dealing with bi-directional languages like Hebrew and English. This often led to a confusing and inaccessible experience for users relying on assistive technologies, where content would be read from right-to-left in English or left-to-right in Hebrew.

This project addresses that exact pain point. It is a **Python-based web application (Flask)** designed to streamline the process of making PDF tables accessible by correcting their reading order for screen readers.

## ✨ Key Features

-   **PDF Upload & Analysis:** Upload any PDF document and the tool automatically identifies tables within it.
-   **Page-Specific Control:** Users can select specific pages for table remediation, allowing for precise control.
-   **Automated Table Tag Reversal:** Generates a new PDF with corrected table tags, ensuring the logical reading order for screen readers (e.g., inverting right-to-left for English tables, and left-to-right for Hebrew tables).
-   **User-Friendly Interface:** Provides an intuitive web interface for easy interaction and seamless workflow.
-   **Enhanced Accessibility:** Directly improves the experience for users of assistive technologies, promoting digital inclusion.

## 🚀 How it Works

The application uses Python to:
1.  Receive a PDF document via a web interface.
2.  Parse the PDF to detect existing tables.
3.  Allows the user to specify which pages require remediation.
4.  Processes the selected pages, effectively "reversing" the table reading order tags.
5.  Outputs a new, accessible PDF document.
## 🖼️ Image of the interface in action
<img width="465" height="470" alt="image" src="https://github.com/user-attachments/assets/4bbf3c37-028b-411e-a8fb-38ce5a39f116" />

## 🛠️ Technologies Used

-   **Python 3.x:** Core programming language.
-   **Flask:** For building the lightweight web interface.
-   **PDF Libraries:** pikepdf
-   **HTML/CSS/JavaScript:** For the front-end user experience.

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/michalitaub/reverse_tables.git](https://github.com/michalitaub/reverse_tables.git)
    cd reverse_tables
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## ▶️ Usage

1.  **Run the application:**
    ```bash
    python app.py
    ```
2.  Open your web browser and navigate to `http://127.0.0.1:5000` (or the address shown in your console).
3.  Upload your PDF, select the desired pages, and generate your accessible document!


---
