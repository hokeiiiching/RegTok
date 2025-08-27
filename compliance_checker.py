import os
import google.generativeai as genai
from dotenv import load_dotenv

def get_llm_response(text_input: str) -> str:
    """
    Takes a text input and gets a response from the Gemini LLM.

    Args:
        text_input: The user's text (e.g., a feature description).

    Returns:
        The response text from the LLM, or an error message.
    """
    try:
        # Load environment variables from the .env file
        load_dotenv()

        # Check if the API key is available
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "Error: GOOGLE_API_KEY not found. Please set it in your .env file."

        # Configure the generative AI client
        genai.configure(api_key=api_key)

        # Initialize the model
        # Using 'gemini-pro' as it is a powerful and versatile model
        model = genai.GenerativeModel('gemini-pro')

        # Generate content
        response = model.generate_content(text_input)

        return response.text

    except Exception as e:
        # Handle potential errors during the API call
        return f"An error occurred: {e}"

# This block allows you to run this script directly for testing
if __name__ == "__main__":
    print("Welcome to the LLM Baseline Tester.")
    print("Type 'exit' to quit.")

    # Loop to allow for continuous testing
    while True:
        # Get user input from the command line
        user_input = input("\nEnter your feature description: ")

        if user_input.lower() == 'exit':
            break

        # Get the response from the LLM
        llm_response = get_llm_response(user_input)

        # Print the response in a formatted way
        print("\n--- LLM Response ---")
        print(llm_response)
        print("--------------------\n")