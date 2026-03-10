import numpy as np
import pandas as pd
from scipy.interpolate import griddata, interp1d, RectBivariateSpline
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

class VolatilitySurface:
    """
    Implied Volatility Surface (Volatility Smile/Skew) Model 
    Based on John Hull's Options, Futures, and Other Derivatives (Ch. 20)
    
    This module takes an empirical option chain (with varying strikes and expirations)
    and constructs a mathematical surface to interpolate the implied volatility
    for any arbitrary strike and expiration.
    """
    
    def __init__(self):
        self.surface_data = None
        self._spline = None
        self._is_fitted = False
        
    def fit_surface(self, option_chain_df: pd.DataFrame, current_stock_price: float):
        """
        Fits a 2D Volatility Surface based on the provided option chain.
        
        Args:
            option_chain_df: DataFrame containing ['strike', 'dte' (days to expiry), 'implied_volatility']
            current_stock_price: Current underlying price used for moneyness calculation.
        """
        try:
            # Filter out invalid IVs
            valid_df = option_chain_df[
                (option_chain_df['implied_volatility'].notna()) & 
                (option_chain_df['implied_volatility'] > 0.0) &
                (option_chain_df['implied_volatility'] < 3.0)  # Filter extreme spikes
            ].copy()
            
            if len(valid_df) < 5:
                logger.warning("Not enough valid data points to build Volatility Surface.")
                return False
                
            # Use Moneyness (K / S) instead of absolute strike for better interpolation
            valid_df['moneyness'] = valid_df['strike'] / current_stock_price
            
            # Store data
            self.surface_data = valid_df
            
            # Prepare grid for 2D interpolation
            # We use moneyness and 'dte' (days to expiry)
            self._x_moneyness = valid_df['moneyness'].values
            self._y_dte = valid_df['dte'].values
            self._z_iv = valid_df['implied_volatility'].values
            
            self._is_fitted = True
            logger.info(f"Volatility Surface fitted with {len(valid_df)} data points.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to fit Volatility Surface: {e}")
            self._is_fitted = False
            return False

    def get_iv(self, strike: float, time_to_expiration_days: float, current_stock_price: float) -> float:
        """
        Get the interpolated Implied Volatility for a specific strike and DTE.
        Uses griddata for scattered 2D interpolation.
        
        Args:
            strike: Target strike price
            time_to_expiration_days: Days to expiration
            current_stock_price: Current price of the underlying asset
            
        Returns:
            Calculated Implied Volatility (float)
        """
        if not self._is_fitted or self.surface_data is None:
            logger.warning("Volatility Surface is not fitted. Returning default IV.")
            return 0.20 # Fallback default
            
        try:
            target_moneyness = strike / current_stock_price
            
            # griddata expects points as (N, 2) array and xi as (1, 2)
            points = np.column_stack((self._x_moneyness, self._y_dte))
            xi = np.array([[target_moneyness, time_to_expiration_days]])
            
            # Perform unstructured 2D interpolation
            interpolated_iv = griddata(
                points=points,
                values=self._z_iv,
                xi=xi,
                method='linear'
            )
            
            # If the point is outside the convex hull, griddata returns nan, fallback to nearest
            if np.isnan(interpolated_iv[0]):
                interpolated_iv = griddata(
                    points=points,
                    values=self._z_iv,
                    xi=xi,
                    method='nearest'
                )
                
            return float(interpolated_iv[0])
        except Exception as e:
            logger.error(f"Error interpolating IV from surface: {e}")
            return float(np.median(self._z_iv)) # Fallback to median IV if error occurs
            
    def get_volatility_smile(self, time_to_expiration_days: float, 
                             current_stock_price: float, 
                             moneyness_range: Tuple[float, float] = (0.7, 1.3),
                             steps: int = 50) -> pd.DataFrame:
        """
        Generates a 1D Volatility Smile curve for a specific expiration date.
        Useful for visualization.
        """
        if not self._is_fitted:
            return pd.DataFrame()
            
        moneyness_points = np.linspace(moneyness_range[0], moneyness_range[1], steps)
        strikes = moneyness_points * current_stock_price
        
        ivs = []
        for strike in strikes:
            ivs.append(self.get_iv(strike, time_to_expiration_days, current_stock_price))
            
        return pd.DataFrame({
            'strike': strikes,
            'moneyness': moneyness_points,
            'implied_volatility': ivs
        })
