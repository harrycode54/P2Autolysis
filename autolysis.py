import argparse
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import openai
from sklearn.cluster import KMeans
import os

# Constants
OUTPUT_DIR = "./"

# Initialize OpenAI API
openai.api_key = os.getenv("AIPROXY_TOKEN")
if not openai.api_key:
    raise ValueError("AIPROXY_TOKEN environment variable is not set.")

openai.api_base = "https://aiproxy.sanand.workers.dev/openai/v1"

def load_dataset(filename):
    """Load and preprocess the dataset."""
    try:
        data = pd.read_csv(filename, encoding="latin1")
        print(f"Dataset loaded: {data.shape[0]} rows, {data.shape[1]} columns.")
        return data
    except FileNotFoundError:
        print(f"Error: File not found: {filename}")
        return None  # Return None on error
    except pd.errors.ParserError:
        print(f"Error: Could not parse CSV. Check format.")
        return None
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return None

def basic_analysis(data):
    """Perform basic data analysis."""
    if data is None:
        return None
    summary = {
        "shape": data.shape,
        "columns": data.dtypes.to_dict(),
        "missing_values": data.isnull().sum().to_dict(),
        "summary_statistics": data.describe().to_dict()
    }
    return summary

def visualize_correlation(data):
    """Generate a correlation heatmap."""
    if data is None:
        return None
    numerical_data = data.select_dtypes(include=np.number)
    if numerical_data.empty:
        print("No numeric data for correlation analysis.")
        return None
    corr = numerical_data.corr()
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm")
    heatmap_path = os.path.join(OUTPUT_DIR, "correlation_heatmap.png")
    plt.savefig(heatmap_path)
    plt.close()
    print(f"Heatmap saved: {heatmap_path}")
    return heatmap_path

def cluster_analysis(data):
    """Perform clustering."""
    if data is None:
        return None
    numerical_data = data.select_dtypes(include=np.number).dropna()
    if numerical_data.shape[0] < 2:
        print("Not enough data points for clustering.")
        return None

    n_clusters = min(3, numerical_data.shape[0])
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
    clusters = kmeans.fit_predict(numerical_data)

    data["Cluster"] = np.nan
    data.loc[numerical_data.index, "Cluster"] = clusters

    plt.figure(figsize=(8, 6))
    if numerical_data.shape[1] >= 2:
        sns.scatterplot(x=numerical_data.iloc[:, 0], y=numerical_data.iloc[:, 1], hue=clusters, palette="viridis")
        plt.xlabel(numerical_data.columns[0])
        plt.ylabel(numerical_data.columns[1])
    else:
        sns.histplot(x=numerical_data.iloc[:, 0], hue=clusters, palette='viridis')
        plt.xlabel(numerical_data.columns[0])
    plt.title("Cluster Analysis")
    cluster_path = os.path.join(OUTPUT_DIR, "cluster_plot.png")
    plt.savefig(cluster_path)
    plt.close()
    print(f"Cluster plot saved: {cluster_path}")
    return cluster_path

def query_llm(prompt):
    """Query the LLM."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": prompt}],
            max_tokens=700
        )
        return response['choices'][0]['message']['content'].strip()
    except openai.error.OpenAIError as e:
        print(f"OpenAI API error: {e}")
        return f"OpenAI API Error: {e}"
    except Exception as e:
        print(f"LLM query error: {e}")
        return f"LLM Query Error: {e}"

def narrate_story(data_summary, insights, visuals):
    """Create narrative and save to README.md."""
    prompt = (f"Dataset summary: {data_summary}.\nInsights: {insights}.\n"
              f"Write a detailed story. Reference visuals if provided.")
    story = query_llm(prompt)

    readme_path = os.path.join(OUTPUT_DIR, "README.md")
    with open(readme_path, "w") as f:
        f.write(story)
        if visuals[0]:
            f.write(f"\n\n![Correlation Heatmap]({os.path.basename(visuals[0])})")
        if visuals[1]:
            f.write(f"\n\n![Cluster Plot]({os.path.basename(visuals[1])})")
    print(f"Narrative saved to: {readme_path}")

def main():
    parser = argparse.ArgumentParser(description="Dataset analysis and storytelling.")
    parser.add_argument("filename", help="Path to the CSV file.")
    args = parser.parse_args()

    data = load_dataset(args.filename)
    if data is None:
        return  # Exit if data loading failed

    summary = basic_analysis(data)
    if summary is None:
        return

    heatmap_path = visualize_correlation(data)
    cluster_path = cluster_analysis(data)

    insights_prompt = f"Analyze this dataset summary: {summary}"
    insights = query_llm(insights_prompt)

    visuals = [heatmap_path, cluster_path]
    narrate_story(summary, insights, visuals)

if __name__ == "__main__":
    main()