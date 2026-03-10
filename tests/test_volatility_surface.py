import pandas as pd
import numpy as np
from calculation_layer.module24_volatility_surface import VolatilitySurface

def test_volatility_surface():
    print("=== Testing Volatility Surface Interpolation ===")
    
    # Mock Option Chain Data
    # 3 Expirations: 30 days, 60 days, 90 days (0.08, 0.16, 0.25 years roughly)
    # Strikes around S=100
    mock_data = {
        'strike': [
            90, 95, 100, 105, 110,  # 30 DTE
            90, 95, 100, 105, 110,  # 60 DTE
            90, 95, 100, 105, 110   # 90 DTE
        ],
        'dte': [
            30, 30, 30, 30, 30,
            60, 60, 60, 60, 60,
            90, 90, 90, 90, 90
        ],
        'implied_volatility': [
            0.25, 0.22, 0.20, 0.19, 0.21, # Smile 30 DTE
            0.24, 0.21, 0.19, 0.18, 0.20, # Smile 60 DTE
            0.23, 0.20, 0.18, 0.17, 0.19  # Smile 90 DTE
        ]
    }
    
    df = pd.DataFrame(mock_data)
    S = 100.0
    
    surface = VolatilitySurface()
    
    # Test Fitting
    success = surface.fit_surface(df, S)
    print(f"Surface Fitting Success: {success}")
    assert success
    
    # Test Exact Point Interpolation (Should match exactly)
    iv_exact = surface.get_iv(100, 30, S)
    print(f"Exact Point (K=100, DTE=30) IV: {iv_exact:.4f} (Expected: 0.2000)")
    assert abs(iv_exact - 0.20) < 0.001
    
    # Test Linear Interpolation Between Strikes (K=97.5, DTE=30)
    # Should be halfway between 0.22 and 0.20 = 0.21
    iv_interp_strike = surface.get_iv(97.5, 30, S)
    print(f"Interpolated Strike (K=97.5, DTE=30) IV: {iv_interp_strike:.4f} (Expected: ~0.2100)")
    
    # Test Linear Interpolation Between DTEs (K=100, DTE=45)
    # Should be halfway between 0.20 (30 DTE) and 0.19 (60 DTE) = 0.195
    iv_interp_dte = surface.get_iv(100, 45, S)
    print(f"Interpolated DTE (K=100, DTE=45) IV: {iv_interp_dte:.4f} (Expected: ~0.1950)")
    
    # Test Extrapolation (Outside Convex Hull fallback to nearest)
    # K=120, DTE=30 -> Nearest is K=110, DTE=30 -> IV=0.21
    iv_extrap = surface.get_iv(120, 30, S)
    print(f"Extrapolated Point (K=120, DTE=30) IV: {iv_extrap:.4f} (Expected: 0.2100 nearest)")
    
    # Test Smile Generation
    smile_df = surface.get_volatility_smile(30, S, (0.8, 1.2), 5)
    print("\nGenerated Volatility Smile (30 DTE):")
    print(smile_df.to_string(index=False))

if __name__ == "__main__":
    test_volatility_surface()
