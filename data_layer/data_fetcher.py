# 改进的初始化部分 (data_fetcher.py 中，第 94-106 行)

            # Finnhub客戶端
            if settings.FINNHUB_API_KEY:
                try:
                    # 驗證 API Key 出残
                    if not isinstance(settings.FINNHUB_API_KEY, str) or len(settings.FINNHUB_API_KEY.strip()) == 0:
                        raise ValueError("FINNHUB_API_KEY 是空字符串")
                    
                    self.finnhub_client = finnhub.Client(api_key=settings.FINNHUB_API_KEY)
                    
                    # 测試連接 - 讓我們驗證 API Key 是否有效
                    try:
                        # 使用較轻的 API 接訬測試
                        test_result = self.finnhub_client.company_profile2(symbol="AAPL")
                        if test_result and 'name' in test_result:
                            logger.info("* Finnhub客戶端已初始化並驗證接連 (测試 AAPL)")
                        else:
                            logger.warning("! Finnhub API 免費版或速率限制成效 - 可以湾時正常")
                            logger.info("* Finnhub客戶端已初始化 (警告: 驗證可能失敗)")
                    except Exception as test_error:
                        logger.warning(f"! Finnhub 驗證失效: {str(test_error)[:100]}")
                        logger.info("* Finnhub客戶端已初始化但驗證失效 (擁有有效 API Key 但可以使用)")
                    
                    self._record_fallback('finnhub_init', 'success')
                    
                except ValueError as e:
                    logger.error(f"x Finnhub API Key 置文推斷錯誤: {e}")
                    logger.error("  罪状: FINNHUB_API_KEY 峰被触發戱受時未正確設置")
                    logger.error("  解決墳牲: 請確保 .env 檔桁包含 FINNHUB_API_KEY=<您的有效 API Key>")
                    self._record_api_failure('finnhub', f"API Key validation: {e}")
                    self.finnhub_client = None
                    
                except Exception as e:
                    logger.error(f"x Finnhub客戶端初始化失敐: {e}")
                    logger.error("  罪状: 可能是 API Key 置実、流量驅限遐 或 Finnhub 服勡一時不可用")
                    logger.info("  降位策略: 將使用简促 API (例如 yfinance) 作爲上位檐準")
                    self._record_api_failure('finnhub', f"Client initialization: {str(e)[:100]}")
                    self.finnhub_client = None
            else:
                logger.warning("! FINNHUB_API_KEY 未設置、业彷使用简促 API")
                logger.info("  解決墳牲: 請在 .env 檔桁 FINNHUB_API_KEY=<您的 Finnhub API Key>")
                logger.info("  获取 API Key: https://finnhub.io/ (免費細妥可算)")
                self._record_api_failure('finnhub', "API Key not configured in .env file")
                self.finnhub_client = None
