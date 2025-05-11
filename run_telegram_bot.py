import logging
import os
import telegram_bot_simple
import market_analysis
import groq_ai
import argparse
import json

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_analyze_all_pairs():
    """Run analysis on all supported currency pairs and print results."""
    logger.info("Running tests for all currency pairs...")
    
    # All supported currency pairs
    currency_pairs = [
        "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD", "BTCUSD", "ETHUSD"
    ]
    
    for pair in currency_pairs:
        logger.info(f"Analyzing {pair}...")
        
        # Get market analysis
        analysis = market_analysis.analyze_market(pair, use_ai=True)
        
        # Print basic analysis
        logger.info(f"{pair} Analysis:")
        logger.info(f"  Price: {analysis.get('current_price', 'N/A')}")
        logger.info(f"  Trend: {analysis.get('trend', 'N/A')}")
        logger.info(f"  Recommendation: {analysis.get('recommendation', 'N/A')}")
        logger.info(f"  Confidence: {analysis.get('confidence', 'N/A')}%")
        
        # Get AI trading plan
        if "ai_analysis" in analysis:
            ai_analysis = analysis["ai_analysis"]
            
            # Try to get a trade evaluation
            try:
                trade_plan = groq_ai.evaluate_trade_opportunity(analysis, pair)
                if trade_plan and not trade_plan.get("ai_error", False):
                    if trade_plan.get("execute_trade", False):
                        logger.info(f"  AI Trade Recommendation: {trade_plan.get('trade_type', 'unknown').upper()}")
                        logger.info(f"  Entry: {trade_plan.get('entry_price', 'N/A')}")
                        logger.info(f"  Stop Loss: {trade_plan.get('stop_loss', 'N/A')}")
                        logger.info(f"  Take Profit: {trade_plan.get('take_profit', 'N/A')}")
                    else:
                        logger.info(f"  AI Trade Recommendation: HOLD/NO TRADE")
            except Exception as e:
                logger.error(f"Error getting trade evaluation: {str(e)}")
        
        # Save analysis to file
        try:
            filename = f"analysis_{pair}_{analysis.get('timestamp', '').replace(' ', '_').replace(':', '')}.json"
            with open(filename, 'w') as f:
                json.dump(analysis, f, indent=2)
            logger.info(f"  Analysis saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving analysis to file: {str(e)}")
        
        logger.info("------------------------")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the trading bot Telegram interface")
    parser.add_argument("--test", action="store_true", help="Run tests on all currency pairs")
    args = parser.parse_args()
    
    # If test mode, run analysis on all pairs
    if args.test:
        test_analyze_all_pairs()
        return
    
    # Check if we have a Telegram token
    if not os.environ.get("TELEGRAM_TOKEN"):
        logger.error("No TELEGRAM_TOKEN provided. Please set the TELEGRAM_TOKEN environment variable.")
        return
    
    logger.info("Starting Telegram bot...")
    telegram_bot_simple.main()

if __name__ == "__main__":
    main()