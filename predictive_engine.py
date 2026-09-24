import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

def compute_descriptive_stats(df: pd.DataFrame, num_cols: List[str]) -> Dict[str, Any]:
    """
    Computes comprehensive descriptive metrics for all numeric columns.
    """
    stats = {}
    for col in num_cols:
        series = df[col].dropna()
        if len(series) == 0:
            continue
            
        q25 = float(series.quantile(0.25))
        q75 = float(series.quantile(0.75))
        iqr = q75 - q25
        lower_bound = q25 - 1.5 * iqr
        upper_bound = q75 + 1.5 * iqr
        outliers_count = int(((series < lower_bound) | (series > upper_bound)).sum())
        
        mean_val = float(series.mean())
        std_val = float(series.std()) if len(series) > 1 else 0.0
        
        stats[col] = {
            "count": int(len(series)),
            "mean": round(mean_val, 2),
            "std": round(std_val, 2),
            "min": round(float(series.min()), 2),
            "q25": round(q25, 2),
            "median": round(float(series.median()), 2),
            "q75": round(q75, 2),
            "max": round(float(series.max()), 2),
            "outliers_count": outliers_count,
            "skewness": round(float(series.skew()), 2) if len(series) > 2 else 0.0
        }
    return stats

def compute_correlation_analysis(df: pd.DataFrame, num_cols: List[str]) -> Dict[str, Any]:
    """
    Computes correlation matrix and extracts strongest relationships.
    """
    if len(num_cols) < 2:
        return {"matrix": {}, "top_correlations": []}
        
    corr_df = df[num_cols].corr().round(3)
    corr_matrix = corr_df.to_dict()
    
    # Extract pairs
    pairs = []
    seen = set()
    for col1 in num_cols:
        for col2 in num_cols:
            if col1 != col2 and (col2, col1) not in seen:
                seen.add((col1, col2))
                val = corr_df.loc[col1, col2]
                if not pd.isna(val):
                    pairs.append({
                        "col1": col1,
                        "col2": col2,
                        "correlation": float(val),
                        "strength": "Strong" if abs(val) >= 0.7 else ("Moderate" if abs(val) >= 0.4 else "Weak"),
                        "direction": "Positive" if val > 0 else "Negative"
                    })
                    
    pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)
    return {
        "matrix": corr_matrix,
        "columns": num_cols,
        "top_correlations": pairs[:8]
    }

def run_linear_regression(
    df: pd.DataFrame,
    feature_col: Optional[str] = None,
    target_col: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Fits linear regression between feature_col (X) and target_col (Y),
    computes trendline equation, R2, and generates forecast points.
    """
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    # Filter out ID columns
    usable_cols = [c for c in num_cols if not c.lower().endswith('id') and c.lower() != 'id']
    if len(usable_cols) < 2:
        usable_cols = num_cols
        
    if len(usable_cols) < 2:
        return None
        
    if not feature_col or feature_col not in usable_cols:
        feature_col = usable_cols[0]
    if not target_col or target_col not in usable_cols or target_col == feature_col:
        target_col = usable_cols[1] if usable_cols[1] != feature_col else usable_cols[0]
        
    sub_df = df[[feature_col, target_col]].dropna()
    if len(sub_df) < 3:
        return None
        
    x = sub_df[feature_col].values.astype(float)
    y = sub_df[target_col].values.astype(float)
    
    # Fit line: y = m*x + c
    try:
        slope, intercept = np.polyfit(x, y, 1)
        y_pred = slope * x + intercept
        
        # R-squared calculation
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        r2 = max(0.0, min(1.0, float(r2)))
        
        # Sample points for visualization (sorted by x)
        sort_idx = np.argsort(x)
        sample_size = min(30, len(x))
        step = max(1, len(x) // sample_size)
        sampled_indices = sort_idx[::step]
        
        actual_points = [{"x": round(float(x[i]), 2), "y": round(float(y[i]), 2)} for i in sampled_indices]
        trend_points = [{"x": round(float(x[i]), 2), "y": round(float(y_pred[i]), 2)} for i in sampled_indices]
        
        # Generate 5 future forecast points
        x_min, x_max = float(np.min(x)), float(np.max(x))
        x_range = x_max - x_min if x_max > x_min else 1.0
        forecast_step = x_range * 0.1
        
        forecast_points = []
        for i in range(1, 6):
            proj_x = x_max + i * forecast_step
            proj_y = slope * proj_x + intercept
            forecast_points.append({"x": round(proj_x, 2), "y": round(float(proj_y), 2)})
            
        sign = "+" if intercept >= 0 else "-"
        equation = f"{target_col} = {slope:.3f} × {feature_col} {sign} {abs(intercept):.3f}"
        
        # Narrative Insight
        relationship_type = "positive" if slope > 0 else "negative"
        fit_strength = "strong" if r2 >= 0.7 else ("moderate" if r2 >= 0.4 else "weak")
        narrative = (
            f"A {fit_strength} {relationship_type} linear trend exists between {feature_col} and {target_col} "
            f"(R² = {r2:.3f}). For every 1 unit increase in {feature_col}, {target_col} is estimated to change by "
            f"{slope:+.3f} units."
        )
        
        return {
            "feature": feature_col,
            "target": target_col,
            "slope": round(float(slope), 4),
            "intercept": round(float(intercept), 4),
            "r2_score": round(r2, 4),
            "equation": equation,
            "narrative": narrative,
            "actual_points": actual_points,
            "trend_points": trend_points,
            "forecast_points": forecast_points,
            "available_features": usable_cols
        }
    except Exception as e:
        return {"error": str(e)}

def analyze_dataset_predictions(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Main predictive analysis orchestrator:
    - Detects numeric variables
    - Calculates statistics & outliers
    - Performs correlation matrix analysis
    - Fits best-fit regression model and forecast
    """
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    if len(num_cols) == 0:
        return {
            "has_numeric": False,
            "message": "No numeric columns detected in this dataset for predictive modeling."
        }
        
    stats = compute_descriptive_stats(df, num_cols)
    correlations = compute_correlation_analysis(df, num_cols)
    
    # Pick strongest pair for initial regression
    feature_col = None
    target_col = None
    if correlations["top_correlations"]:
        top = correlations["top_correlations"][0]
        feature_col = top["col1"]
        target_col = top["col2"]
        
    regression = run_linear_regression(df, feature_col, target_col)
    
    return {
        "has_numeric": True,
        "numeric_columns": num_cols,
        "descriptive_stats": stats,
        "correlations": correlations,
        "regression": regression
    }

if __name__ == '__main__':
    # Test with dummy student DataFrame
    sample_df = pd.DataFrame({
        "year": [1, 2, 3, 4, 1, 2, 3, 4],
        "cgpa": [7.5, 8.2, 8.8, 9.4, 7.1, 7.9, 8.5, 9.1]
    })
    res = analyze_dataset_predictions(sample_df)
    print("Predictive Engine Test:")
    print("Numeric cols:", res["numeric_columns"])
    print("Regression equation:", res["regression"]["equation"])
    print("Narrative:", res["regression"]["narrative"])
