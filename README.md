# ThoughtPrint

## Description

ThoughtPrint is a compact desktop application that sends your prompt to an AI, and "prints" the AI's response directly into both PDF and Markdown files without showing them first. It's designed for viewing AI-generated content as though they are just local files.

## Features

*   **Capture Thoughts:** Enter any text prompt into a simple, always-on-top input window.
*   **AI Processing:** Your prompt is sent to a configured AI model (supports Ollama and OpenAI-compatible APIs).
*   **PDF & Markdown Output:** The AI's response is saved as:
    *   A PDF file, generated using `pandoc` and `xelatex` for high-quality rendering, including support for mathematical formulas and CJK characters.
    *   A raw Markdown (`.md`) file containing the AI's direct response.
*   **Organized Storage:** Output files are saved in a `ThoughtPrint` subdirectory within your user's Documents folder, with unique UUID-based filenames.
*   **Configurable AI:** Choose your AI provider, model, and system prompt through a `/config` command in the input window).
*   **Simple GUI:** A minimal user interface.
*   **Logging:** Detailed logging for diagnostics.

## Installation

Instructions on how to install and set up the application.

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    ```
2.  Navigate to the project directory:
    ```bash
    cd ThoughtPrint
    ```
3.  Install Python dependencies:
  
4.  **Install External Dependencies:**
    *   **Pandoc:** Required for generating PDF files. Download and install from [pandoc.org](https://pandoc.org/installing.html).
    *   **XeLaTeX:** A TeX distribution (like TeX Live or MiKTeX) that includes `xelatex` is required for PDF generation, especially for math and CJK character support. Ensure `xelatex` is in your system's PATH.
    *   **Fonts:** Ensure necessary fonts (e.g., SimSun for Chinese, and fonts for mathematical symbols) are available to XeLaTeX.

## Usage

You can run the application in one of the following ways:

1.  **Double-click:** Locate the `run_app.pyw` file in the project directory and double-click it.
    *(This method is typically for Windows users and assumes Python is correctly associated with `.pyw` files.)*

2.  **Using the command line:**
    ```bash
    python -m ThoughtPrint.main
    ```
