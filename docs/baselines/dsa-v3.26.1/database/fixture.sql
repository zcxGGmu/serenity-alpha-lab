PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE agent_provider_turns (
	id INTEGER NOT NULL,
	session_id VARCHAR(100) NOT NULL,
	run_id VARCHAR(64) NOT NULL,
	provider VARCHAR(64) NOT NULL,
	model VARCHAR(160) NOT NULL,
	anchor_user_message_id INTEGER NOT NULL,
	anchor_assistant_message_id INTEGER NOT NULL,
	messages_json TEXT NOT NULL,
	contains_reasoning BOOLEAN NOT NULL,
	contains_tool_calls BOOLEAN NOT NULL,
	contains_thinking_blocks BOOLEAN NOT NULL,
	must_roundtrip BOOLEAN NOT NULL,
	estimated_tokens INTEGER NOT NULL,
	created_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE alert_cooldowns (
	id INTEGER NOT NULL,
	rule_id INTEGER,
	rule_key VARCHAR(255),
	target VARCHAR(64) NOT NULL,
	severity VARCHAR(16) NOT NULL,
	last_triggered_at DATETIME,
	cooldown_until DATETIME,
	reason TEXT,
	state VARCHAR(16) NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uix_alert_cooldown_rule_target_severity UNIQUE (rule_id, target, severity)
);
CREATE TABLE alert_notifications (
	id INTEGER NOT NULL,
	trigger_id INTEGER,
	channel VARCHAR(32) NOT NULL,
	attempt INTEGER NOT NULL,
	success BOOLEAN NOT NULL,
	error_code VARCHAR(64),
	retryable BOOLEAN NOT NULL,
	latency_ms INTEGER,
	diagnostics TEXT,
	created_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE alert_rules (
	id INTEGER NOT NULL,
	name VARCHAR(64) NOT NULL,
	target_scope VARCHAR(32) NOT NULL,
	target VARCHAR(64) NOT NULL,
	alert_type VARCHAR(32) NOT NULL,
	parameters TEXT NOT NULL,
	severity VARCHAR(16) NOT NULL,
	enabled BOOLEAN NOT NULL,
	source VARCHAR(16) NOT NULL,
	cooldown_policy TEXT,
	notification_policy TEXT,
	created_at DATETIME,
	updated_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE alert_triggers (
	id INTEGER NOT NULL,
	rule_id INTEGER,
	target VARCHAR(64) NOT NULL,
	observed_value FLOAT,
	threshold FLOAT,
	reason TEXT,
	data_source VARCHAR(64),
	data_timestamp DATETIME,
	triggered_at DATETIME,
	status VARCHAR(16) NOT NULL,
	diagnostics TEXT,
	PRIMARY KEY (id)
);
CREATE TABLE analysis_history (
	id INTEGER NOT NULL,
	query_id VARCHAR(64),
	code VARCHAR(10) NOT NULL,
	name VARCHAR(50),
	report_type VARCHAR(16),
	sentiment_score INTEGER,
	operation_advice VARCHAR(20),
	trend_prediction VARCHAR(50),
	analysis_summary TEXT,
	raw_result TEXT,
	news_content TEXT,
	context_snapshot TEXT,
	ideal_buy FLOAT,
	secondary_buy FLOAT,
	stop_loss FLOAT,
	take_profit FLOAT,
	created_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE backtest_results (
	id INTEGER NOT NULL,
	analysis_history_id INTEGER NOT NULL,
	code VARCHAR(10) NOT NULL,
	analysis_date DATE,
	eval_window_days INTEGER NOT NULL,
	engine_version VARCHAR(16) NOT NULL,
	eval_status VARCHAR(16) NOT NULL,
	evaluated_at DATETIME,
	operation_advice VARCHAR(20),
	position_recommendation VARCHAR(8),
	start_price FLOAT,
	end_close FLOAT,
	max_high FLOAT,
	min_low FLOAT,
	stock_return_pct FLOAT,
	direction_expected VARCHAR(16),
	direction_correct BOOLEAN,
	outcome VARCHAR(16),
	stop_loss FLOAT,
	take_profit FLOAT,
	hit_stop_loss BOOLEAN,
	hit_take_profit BOOLEAN,
	first_hit VARCHAR(16),
	first_hit_date DATE,
	first_hit_trading_days INTEGER,
	simulated_entry_price FLOAT,
	simulated_exit_price FLOAT,
	simulated_exit_reason VARCHAR(24),
	simulated_return_pct FLOAT,
	PRIMARY KEY (id),
	CONSTRAINT uix_backtest_analysis_window_version UNIQUE (analysis_history_id, eval_window_days, engine_version),
	FOREIGN KEY(analysis_history_id) REFERENCES analysis_history (id)
);
CREATE TABLE backtest_summaries (
	id INTEGER NOT NULL,
	scope VARCHAR(16) NOT NULL,
	code VARCHAR(16),
	eval_window_days INTEGER NOT NULL,
	engine_version VARCHAR(16) NOT NULL,
	computed_at DATETIME,
	total_evaluations INTEGER,
	completed_count INTEGER,
	insufficient_count INTEGER,
	long_count INTEGER,
	cash_count INTEGER,
	win_count INTEGER,
	loss_count INTEGER,
	neutral_count INTEGER,
	direction_accuracy_pct FLOAT,
	win_rate_pct FLOAT,
	neutral_rate_pct FLOAT,
	avg_stock_return_pct FLOAT,
	avg_simulated_return_pct FLOAT,
	stop_loss_trigger_rate FLOAT,
	take_profit_trigger_rate FLOAT,
	ambiguous_rate FLOAT,
	avg_days_to_first_hit FLOAT,
	advice_breakdown_json TEXT,
	diagnostics_json TEXT,
	PRIMARY KEY (id),
	CONSTRAINT uix_backtest_summary_scope_code_window_version UNIQUE (scope, code, eval_window_days, engine_version)
);
CREATE TABLE conversation_messages (
	id INTEGER NOT NULL,
	session_id VARCHAR(100) NOT NULL,
	role VARCHAR(20) NOT NULL,
	content TEXT NOT NULL,
	created_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE conversation_summaries (
	id INTEGER NOT NULL,
	session_id VARCHAR(100) NOT NULL,
	summary TEXT NOT NULL,
	covered_message_id INTEGER NOT NULL,
	source_message_count INTEGER NOT NULL,
	estimated_tokens INTEGER NOT NULL,
	created_at DATETIME,
	updated_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE decision_signal_feedback (
	id INTEGER NOT NULL,
	signal_id INTEGER NOT NULL,
	feedback_value VARCHAR(16) NOT NULL,
	reason_code VARCHAR(64),
	note TEXT,
	source VARCHAR(16) NOT NULL,
	created_at DATETIME,
	updated_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE decision_signal_outcomes (
	id INTEGER NOT NULL,
	signal_id INTEGER NOT NULL,
	horizon VARCHAR(16) NOT NULL,
	engine_version VARCHAR(32) NOT NULL,
	eval_status VARCHAR(24) NOT NULL,
	outcome VARCHAR(16),
	direction_expected VARCHAR(16),
	direction_correct BOOLEAN,
	unable_reason VARCHAR(64),
	anchor_date DATE,
	eval_window_days INTEGER,
	start_price FLOAT,
	end_close FLOAT,
	max_high FLOAT,
	min_low FLOAT,
	stock_return_pct FLOAT,
	action VARCHAR(16),
	market VARCHAR(8),
	market_phase VARCHAR(24),
	source_type VARCHAR(32),
	source_agent VARCHAR(64),
	plan_quality VARCHAR(16),
	data_quality_level VARCHAR(24),
	holding_state VARCHAR(16) NOT NULL,
	created_at DATETIME,
	updated_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uix_decision_signal_outcome_key UNIQUE (signal_id, horizon, engine_version)
);
CREATE TABLE decision_signals (
	id INTEGER NOT NULL,
	stock_code VARCHAR(16) NOT NULL,
	stock_name VARCHAR(64),
	market VARCHAR(8) NOT NULL,
	source_type VARCHAR(32) NOT NULL,
	source_agent VARCHAR(64),
	source_report_id INTEGER,
	trace_id VARCHAR(64),
	decision_profile VARCHAR(16),
	market_phase VARCHAR(24),
	trigger_source VARCHAR(64) NOT NULL,
	action VARCHAR(16) NOT NULL,
	action_label VARCHAR(32),
	confidence FLOAT,
	score INTEGER,
	horizon VARCHAR(16),
	entry_low FLOAT,
	entry_high FLOAT,
	stop_loss FLOAT,
	target_price FLOAT,
	invalidation TEXT,
	watch_conditions TEXT,
	reason TEXT,
	risk_summary TEXT,
	catalyst_summary TEXT,
	evidence_json TEXT,
	data_quality_summary_json TEXT,
	plan_quality VARCHAR(16) NOT NULL,
	status VARCHAR(16) NOT NULL,
	expires_at DATETIME,
	created_at DATETIME,
	updated_at DATETIME,
	metadata_json TEXT,
	PRIMARY KEY (id)
);
CREATE TABLE fundamental_snapshot (
	id INTEGER NOT NULL,
	query_id VARCHAR(64) NOT NULL,
	code VARCHAR(10) NOT NULL,
	payload TEXT NOT NULL,
	source_chain TEXT,
	coverage TEXT,
	created_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE intelligence_items (
	id INTEGER NOT NULL,
	source_id INTEGER,
	source_name VARCHAR(100),
	source_type VARCHAR(32) NOT NULL,
	title VARCHAR(300) NOT NULL,
	summary TEXT,
	url VARCHAR(1000) NOT NULL,
	source VARCHAR(100),
	published_at DATETIME,
	fetched_at DATETIME,
	scope_type VARCHAR(32) NOT NULL,
	scope_value VARCHAR(64) NOT NULL,
	market VARCHAR(32) NOT NULL,
	raw_payload TEXT,
	PRIMARY KEY (id),
	CONSTRAINT uix_intel_item_source_scope_url UNIQUE (source_id, url, scope_type, scope_value, market),
	FOREIGN KEY(source_id) REFERENCES intelligence_sources (id) ON DELETE SET NULL
);
CREATE TABLE intelligence_sources (
	id INTEGER NOT NULL,
	name VARCHAR(100) NOT NULL,
	source_type VARCHAR(32) NOT NULL,
	url VARCHAR(1000) NOT NULL,
	enabled BOOLEAN NOT NULL,
	scope_type VARCHAR(32) NOT NULL,
	scope_value VARCHAR(64),
	market VARCHAR(32) NOT NULL,
	description TEXT,
	last_status VARCHAR(32),
	last_error TEXT,
	last_fetched_at DATETIME,
	created_at DATETIME,
	updated_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE llm_usage (
	id INTEGER NOT NULL,
	call_type VARCHAR(32) NOT NULL,
	model VARCHAR(128) NOT NULL,
	stock_code VARCHAR(16),
	provider VARCHAR(64),
	prompt_tokens INTEGER NOT NULL,
	completion_tokens INTEGER NOT NULL,
	total_tokens INTEGER NOT NULL,
	provider_usage_json TEXT,
	provider_usage_schema_name VARCHAR(64),
	provider_usage_schema_version VARCHAR(32),
	provider_usage_observed_at VARCHAR(32),
	normalized_prompt_tokens INTEGER,
	normalized_completion_tokens INTEGER,
	normalized_total_tokens INTEGER,
	normalized_cache_read_tokens INTEGER,
	normalized_cache_write_tokens INTEGER,
	normalized_cache_miss_tokens INTEGER,
	normalized_uncached_input_tokens INTEGER,
	normalized_cache_eligible_input_tokens INTEGER,
	normalized_cache_hit_ratio FLOAT,
	normalized_cache_write_ratio FLOAT,
	cache_capability VARCHAR(32),
	cache_eligibility VARCHAR(32),
	cache_observation VARCHAR(32),
	estimated_prefix_tokens INTEGER,
	provider_reported_prompt_tokens INTEGER,
	provider_reported_cached_tokens INTEGER,
	provider_min_cache_tokens INTEGER,
	eligibility_confidence VARCHAR(32),
	tokenizer_name VARCHAR(128),
	tokenizer_version VARCHAR(64),
	messages_hmac VARCHAR(64),
	system_message_hmac VARCHAR(64),
	user_message_hmac VARCHAR(64),
	hmac_key_version VARCHAR(64),
	hmac_domain VARCHAR(32),
	hash_scope VARCHAR(32),
	language VARCHAR(16),
	market_group VARCHAR(16),
	analysis_mode VARCHAR(64),
	legacy_prompt_mode VARCHAR(32),
	skill_config_hmac VARCHAR(64),
	transport VARCHAR(64),
	message_count INTEGER,
	estimated_total_prompt_tokens INTEGER,
	approx_common_prefix_chars INTEGER,
	approx_common_prefix_tokens INTEGER,
	known_dynamic_marker_positions TEXT,
	called_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE news_intel (
	id INTEGER NOT NULL,
	query_id VARCHAR(64),
	code VARCHAR(10) NOT NULL,
	name VARCHAR(50),
	dimension VARCHAR(32),
	"query" VARCHAR(255),
	provider VARCHAR(32),
	title VARCHAR(300) NOT NULL,
	snippet TEXT,
	url VARCHAR(1000) NOT NULL,
	source VARCHAR(100),
	published_date DATETIME,
	fetched_at DATETIME,
	query_source VARCHAR(32),
	requester_platform VARCHAR(20),
	requester_user_id VARCHAR(64),
	requester_user_name VARCHAR(64),
	requester_chat_id VARCHAR(64),
	requester_message_id VARCHAR(64),
	requester_query VARCHAR(255),
	PRIMARY KEY (id),
	CONSTRAINT uix_news_url UNIQUE (url)
);
CREATE TABLE portfolio_accounts (
	id INTEGER NOT NULL,
	owner_id VARCHAR(64),
	name VARCHAR(64) NOT NULL,
	broker VARCHAR(64),
	market VARCHAR(8) NOT NULL,
	base_currency VARCHAR(8) NOT NULL,
	is_active BOOLEAN NOT NULL,
	created_at DATETIME,
	updated_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE portfolio_cash_ledger (
	id INTEGER NOT NULL,
	account_id INTEGER NOT NULL,
	event_date DATE NOT NULL,
	direction VARCHAR(8) NOT NULL,
	amount FLOAT NOT NULL,
	currency VARCHAR(8) NOT NULL,
	note VARCHAR(255),
	created_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(account_id) REFERENCES portfolio_accounts (id)
);
CREATE TABLE portfolio_corporate_actions (
	id INTEGER NOT NULL,
	account_id INTEGER NOT NULL,
	symbol VARCHAR(16) NOT NULL,
	market VARCHAR(8) NOT NULL,
	currency VARCHAR(8) NOT NULL,
	effective_date DATE NOT NULL,
	action_type VARCHAR(24) NOT NULL,
	cash_dividend_per_share FLOAT,
	split_ratio FLOAT,
	note VARCHAR(255),
	created_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(account_id) REFERENCES portfolio_accounts (id)
);
CREATE TABLE portfolio_daily_snapshots (
	id INTEGER NOT NULL,
	account_id INTEGER NOT NULL,
	snapshot_date DATE NOT NULL,
	cost_method VARCHAR(8) NOT NULL,
	base_currency VARCHAR(8) NOT NULL,
	total_cash FLOAT NOT NULL,
	total_market_value FLOAT NOT NULL,
	total_equity FLOAT NOT NULL,
	unrealized_pnl FLOAT NOT NULL,
	realized_pnl FLOAT NOT NULL,
	fee_total FLOAT NOT NULL,
	tax_total FLOAT NOT NULL,
	fx_stale BOOLEAN NOT NULL,
	payload TEXT,
	created_at DATETIME,
	updated_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uix_portfolio_snapshot_account_date_method UNIQUE (account_id, snapshot_date, cost_method),
	FOREIGN KEY(account_id) REFERENCES portfolio_accounts (id)
);
CREATE TABLE portfolio_fx_rates (
	id INTEGER NOT NULL,
	from_currency VARCHAR(8) NOT NULL,
	to_currency VARCHAR(8) NOT NULL,
	rate_date DATE NOT NULL,
	rate FLOAT NOT NULL,
	source VARCHAR(32) NOT NULL,
	is_stale BOOLEAN NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uix_portfolio_fx_pair_date UNIQUE (from_currency, to_currency, rate_date)
);
CREATE TABLE portfolio_position_lots (
	id INTEGER NOT NULL,
	account_id INTEGER NOT NULL,
	cost_method VARCHAR(8) NOT NULL,
	symbol VARCHAR(16) NOT NULL,
	market VARCHAR(8) NOT NULL,
	currency VARCHAR(8) NOT NULL,
	open_date DATE NOT NULL,
	remaining_quantity FLOAT NOT NULL,
	unit_cost FLOAT NOT NULL,
	source_trade_id INTEGER,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(account_id) REFERENCES portfolio_accounts (id),
	FOREIGN KEY(source_trade_id) REFERENCES portfolio_trades (id)
);
CREATE TABLE portfolio_positions (
	id INTEGER NOT NULL,
	account_id INTEGER NOT NULL,
	cost_method VARCHAR(8) NOT NULL,
	symbol VARCHAR(16) NOT NULL,
	market VARCHAR(8) NOT NULL,
	currency VARCHAR(8) NOT NULL,
	quantity FLOAT NOT NULL,
	avg_cost FLOAT NOT NULL,
	total_cost FLOAT NOT NULL,
	last_price FLOAT NOT NULL,
	market_value_base FLOAT NOT NULL,
	unrealized_pnl_base FLOAT NOT NULL,
	valuation_currency VARCHAR(8) NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uix_portfolio_position_account_symbol_market_currency UNIQUE (account_id, symbol, market, currency, cost_method),
	FOREIGN KEY(account_id) REFERENCES portfolio_accounts (id)
);
CREATE TABLE portfolio_trades (
	id INTEGER NOT NULL,
	account_id INTEGER NOT NULL,
	trade_uid VARCHAR(128),
	symbol VARCHAR(16) NOT NULL,
	market VARCHAR(8) NOT NULL,
	currency VARCHAR(8) NOT NULL,
	trade_date DATE NOT NULL,
	side VARCHAR(8) NOT NULL,
	quantity FLOAT NOT NULL,
	price FLOAT NOT NULL,
	fee FLOAT,
	tax FLOAT,
	note VARCHAR(255),
	dedup_hash VARCHAR(64),
	created_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uix_portfolio_trade_uid UNIQUE (account_id, trade_uid),
	CONSTRAINT uix_portfolio_trade_dedup_hash UNIQUE (account_id, dedup_hash),
	FOREIGN KEY(account_id) REFERENCES portfolio_accounts (id)
);
CREATE TABLE schema_migrations (
	version VARCHAR(64) NOT NULL,
	description VARCHAR(255) NOT NULL,
	applied_at DATETIME NOT NULL,
	PRIMARY KEY (version)
);
CREATE TABLE stock_daily (
	id INTEGER NOT NULL,
	code VARCHAR(10) NOT NULL,
	date DATE NOT NULL,
	open FLOAT,
	high FLOAT,
	low FLOAT,
	close FLOAT,
	volume FLOAT,
	amount FLOAT,
	pct_chg FLOAT,
	ma5 FLOAT,
	ma10 FLOAT,
	ma20 FLOAT,
	volume_ratio FLOAT,
	data_source VARCHAR(50),
	created_at DATETIME,
	updated_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uix_code_date UNIQUE (code, date)
);
INSERT INTO "agent_provider_turns" ("id", "session_id", "run_id", "provider", "model", "anchor_user_message_id", "anchor_assistant_message_id", "messages_json", "contains_reasoning", "contains_tool_calls", "contains_thinking_blocks", "must_roundtrip", "estimated_tokens", "created_at") VALUES(1, 'fixture-session-001', 'fixture-run-001', 'fixture-provider', 'fixture-model', 1, 2, '[{"content_hmac":"fixture-user-hmac","role":"user"},{"content_hmac":"fixture-assistant-hmac","role":"assistant"}]', 0, 1, 0, 1, 84, '2026-01-05 15:05:00.000000');
INSERT INTO "alert_cooldowns" ("id", "rule_id", "rule_key", "target", "severity", "last_triggered_at", "cooldown_until", "reason", "state", "updated_at") VALUES(1, 1, 'fixture-price-alert', '600519', 'warning', '2026-01-05 15:05:00.000000', '2026-01-05 15:35:00.000000', 'Synthetic cooldown.', 'active', '2026-01-05 15:05:00.000000');
INSERT INTO "alert_notifications" ("id", "trigger_id", "channel", "attempt", "success", "error_code", "retryable", "latency_ms", "diagnostics", "created_at") VALUES(1, 1, 'fixture', 1, 1, NULL, 0, 12, '{"fixture":true}', '2026-01-05 15:05:00.000000');
INSERT INTO "alert_rules" ("id", "name", "target_scope", "target", "alert_type", "parameters", "severity", "enabled", "source", "cooldown_policy", "notification_policy", "created_at", "updated_at") VALUES(1, 'fixture-price-alert', 'single_symbol', '600519', 'price_above', '{"threshold":1780.0}', 'warning', 1, 'fixture', '{"minutes":30}', '{"channels":["fixture"]}', '2026-01-05 09:30:00.000000', '2026-01-05 09:30:00.000000');
INSERT INTO "alert_triggers" ("id", "rule_id", "target", "observed_value", "threshold", "reason", "data_source", "data_timestamp", "triggered_at", "status", "diagnostics") VALUES(1, 1, '600519', 1781.0, 1780.0, 'Synthetic alert trigger.', 'fixture-provider', '2026-01-05 15:05:00.000000', '2026-01-05 15:05:00.000000', 'triggered', '{"fixture":true}');
INSERT INTO "analysis_history" ("id", "query_id", "code", "name", "report_type", "sentiment_score", "operation_advice", "trend_prediction", "analysis_summary", "raw_result", "news_content", "context_snapshot", "ideal_buy", "secondary_buy", "stop_loss", "take_profit", "created_at") VALUES(1, 'fixture-query-analysis', '600519', 'Fixture Moutai', 'single_stock', 72, 'hold', 'neutral_up', 'Synthetic single stock analysis summary.', '{"code":"600519","decision":{"action":"hold","confidence":0.72},"name":"Fixture Moutai","report_markdown":"# Fixture Single Stock Report\n\nSynthetic baseline report."}', 'Synthetic sanitized news content.', '{"fixture":true,"market":"cn","source":"sanitized"}', 1660.0, 1620.0, 1580.0, 1780.0, '2026-01-05 09:30:00.000000');
INSERT INTO "analysis_history" ("id", "query_id", "code", "name", "report_type", "sentiment_score", "operation_advice", "trend_prediction", "analysis_summary", "raw_result", "news_content", "context_snapshot", "ideal_buy", "secondary_buy", "stop_loss", "take_profit", "created_at") VALUES(2, 'fixture-query-market-review', 'MARKET', 'Fixture Market', 'market_review', 55, 'observe', 'range_bound', 'Synthetic market review summary.', '{"report_markdown":"# Fixture Market Review\n\nSynthetic baseline report."}', 'Synthetic market news.', '{"fixture":true,"market":"cn"}', NULL, NULL, NULL, NULL, '2026-01-05 15:05:00.000000');
INSERT INTO "backtest_results" ("id", "analysis_history_id", "code", "analysis_date", "eval_window_days", "engine_version", "eval_status", "evaluated_at", "operation_advice", "position_recommendation", "start_price", "end_close", "max_high", "min_low", "stock_return_pct", "direction_expected", "direction_correct", "outcome", "stop_loss", "take_profit", "hit_stop_loss", "hit_take_profit", "first_hit", "first_hit_date", "first_hit_trading_days", "simulated_entry_price", "simulated_exit_price", "simulated_exit_reason", "simulated_return_pct") VALUES(1, 1, '600519', '2026-01-05', 10, 'fixture-v1', 'completed', '2026-01-05 15:05:00.000000', 'hold', 'long', 1695.0, 1710.0, 1782.0, 1660.0, 0.885, 'not_down', 1, 'win', 1580.0, 1780.0, 0, 1, 'take_profit', '2026-01-12', 5, 1695.0, 1780.0, 'take_profit', 5.015);
INSERT INTO "backtest_summaries" ("id", "scope", "code", "eval_window_days", "engine_version", "computed_at", "total_evaluations", "completed_count", "insufficient_count", "long_count", "cash_count", "win_count", "loss_count", "neutral_count", "direction_accuracy_pct", "win_rate_pct", "neutral_rate_pct", "avg_stock_return_pct", "avg_simulated_return_pct", "stop_loss_trigger_rate", "take_profit_trigger_rate", "ambiguous_rate", "avg_days_to_first_hit", "advice_breakdown_json", "diagnostics_json") VALUES(1, 'stock', '600519', 10, 'fixture-v1', '2026-01-05 15:05:00.000000', 1, 1, 0, 1, 0, 1, 0, 0, 100.0, 100.0, 0.0, 0.885, 5.015, 0.0, 100.0, 0.0, 5.0, '{"hold":1}', '{"fixture":true}');
INSERT INTO "conversation_messages" ("id", "session_id", "role", "content", "created_at") VALUES(1, 'fixture-session-001', 'user', 'Synthetic user asks for a fixture analysis.', '2026-01-05 09:30:00.000000');
INSERT INTO "conversation_messages" ("id", "session_id", "role", "content", "created_at") VALUES(2, 'fixture-session-001', 'assistant', 'Synthetic assistant response for fixture analysis.', '2026-01-05 15:05:00.000000');
INSERT INTO "conversation_summaries" ("id", "session_id", "summary", "covered_message_id", "source_message_count", "estimated_tokens", "created_at", "updated_at") VALUES(1, 'fixture-session-001', 'Synthetic conversation summary.', 1, 1, 42, '2026-01-05 15:05:00.000000', '2026-01-05 15:05:00.000000');
INSERT INTO "decision_signal_feedback" ("id", "signal_id", "feedback_value", "reason_code", "note", "source", "created_at", "updated_at") VALUES(1, 1, 'useful', 'fixture', 'Synthetic reviewer feedback.', 'fixture', '2026-01-05 15:05:00.000000', '2026-01-05 15:05:00.000000');
INSERT INTO "decision_signal_outcomes" ("id", "signal_id", "horizon", "engine_version", "eval_status", "outcome", "direction_expected", "direction_correct", "unable_reason", "anchor_date", "eval_window_days", "start_price", "end_close", "max_high", "min_low", "stock_return_pct", "action", "market", "market_phase", "source_type", "source_agent", "plan_quality", "data_quality_level", "holding_state", "created_at", "updated_at") VALUES(1, 1, 'swing', 'fixture-v1', 'completed', 'win', 'not_down', 1, NULL, '2026-01-05', 10, 1695.0, 1710.0, 1782.0, 1660.0, 0.885, 'hold', 'cn', 'range', 'analysis', 'fixture-agent', 'complete', 'fixture', 'held', '2026-01-05 15:05:00.000000', '2026-01-05 15:05:00.000000');
INSERT INTO "decision_signals" ("id", "stock_code", "stock_name", "market", "source_type", "source_agent", "source_report_id", "trace_id", "decision_profile", "market_phase", "trigger_source", "action", "action_label", "confidence", "score", "horizon", "entry_low", "entry_high", "stop_loss", "target_price", "invalidation", "watch_conditions", "reason", "risk_summary", "catalyst_summary", "evidence_json", "data_quality_summary_json", "plan_quality", "status", "expires_at", "created_at", "updated_at", "metadata_json") VALUES(1, '600519', 'Fixture Moutai', 'cn', 'analysis', 'fixture-agent', 1, 'fixture-trace-001', 'balanced', 'range', 'fixture', 'hold', 'Hold', 0.72, 72, 'swing', 1660.0, 1700.0, 1580.0, 1780.0, 'Synthetic invalidation condition.', 'Synthetic watch conditions.', 'Synthetic signal reason.', 'Synthetic risk summary.', 'Synthetic catalyst summary.', '[{"kind":"fixture","ref":"analysis_history"}]', '{"level":"fixture"}', 'complete', 'active', '2026-02-05 00:00:00.000000', '2026-01-05 09:30:00.000000', '2026-01-05 09:30:00.000000', '{"decision_profile":"balanced","fixture":true}');
INSERT INTO "fundamental_snapshot" ("id", "query_id", "code", "payload", "source_chain", "coverage", "created_at") VALUES(1, 'fixture-query-analysis', '600519', '{"as_of":"2026-01-05","pe_ttm":24.5,"roe":0.28}', '["fixture-provider"]', '{"fundamental":"synthetic"}', '2026-01-05 09:30:00.000000');
INSERT INTO "intelligence_items" ("id", "source_id", "source_name", "source_type", "title", "summary", "url", "source", "published_at", "fetched_at", "scope_type", "scope_value", "market", "raw_payload") VALUES(1, 1, 'fixture-rss', 'rss', 'Synthetic fixture market headline', 'Synthetic non-personal market context.', 'https://example.invalid/news/fixture-market-headline', 'fixture', '2026-01-05 09:30:00.000000', '2026-01-05 15:05:00.000000', 'market', 'cn', 'cn', '{"fixture":true,"symbols":["600519","000001"]}');
INSERT INTO "intelligence_sources" ("id", "name", "source_type", "url", "enabled", "scope_type", "scope_value", "market", "description", "last_status", "last_error", "last_fetched_at", "created_at", "updated_at") VALUES(1, 'fixture-rss', 'rss', 'https://example.invalid/finance/rss.xml', 1, 'market', 'cn', 'cn', 'Synthetic source for P0 database baseline.', 'ok', NULL, '2026-01-05 09:30:00.000000', '2026-01-05 09:30:00.000000', '2026-01-05 09:30:00.000000');
INSERT INTO "llm_usage" ("id", "call_type", "model", "stock_code", "provider", "prompt_tokens", "completion_tokens", "total_tokens", "provider_usage_json", "provider_usage_schema_name", "provider_usage_schema_version", "provider_usage_observed_at", "normalized_prompt_tokens", "normalized_completion_tokens", "normalized_total_tokens", "normalized_cache_read_tokens", "normalized_cache_write_tokens", "normalized_cache_miss_tokens", "normalized_uncached_input_tokens", "normalized_cache_eligible_input_tokens", "normalized_cache_hit_ratio", "normalized_cache_write_ratio", "cache_capability", "cache_eligibility", "cache_observation", "estimated_prefix_tokens", "provider_reported_prompt_tokens", "provider_reported_cached_tokens", "provider_min_cache_tokens", "eligibility_confidence", "tokenizer_name", "tokenizer_version", "messages_hmac", "system_message_hmac", "user_message_hmac", "hmac_key_version", "hmac_domain", "hash_scope", "language", "market_group", "analysis_mode", "legacy_prompt_mode", "skill_config_hmac", "transport", "message_count", "estimated_total_prompt_tokens", "approx_common_prefix_chars", "approx_common_prefix_tokens", "known_dynamic_marker_positions", "called_at") VALUES(1, 'analysis', 'fixture-model', '600519', 'fixture-provider', 120, 80, 200, '{"completion_tokens":80,"prompt_tokens":120}', 'fixture_usage', '1', '2026-01-05T09:30:00Z', 120, 80, 200, 0, 0, 120, 120, 0, 0.0, 0.0, 'none', 'not_eligible', 'fixture', 0, 120, 0, 0, 'high', NULL, NULL, 'fixture-messages-hmac', 'fixture-system-hmac', 'fixture-user-hmac', 'fixture-v1', 'fixture', 'message_shape', 'zh', 'cn', 'single_stock', 'fixture', 'fixture-skill-hmac', 'offline', 2, 120, 0, 0, '[]', '2026-01-05 15:05:00.000000');
INSERT INTO "news_intel" ("id", "query_id", "code", "name", "dimension", "query", "provider", "title", "snippet", "url", "source", "published_date", "fetched_at", "query_source", "requester_platform", "requester_user_id", "requester_user_name", "requester_chat_id", "requester_message_id", "requester_query") VALUES(1, 'fixture-query-analysis', '600519', 'Fixture Moutai', 'latest_news', 'fixture 600519 latest news', 'fixture', 'Synthetic single stock fixture news', 'Synthetic snippet with no personal data.', 'https://example.invalid/news/600519', 'fixture', '2026-01-05 09:30:00.000000', '2026-01-05 15:05:00.000000', 'ci', 'fixture', 'fixture-user', 'fixture', 'fixture-chat', 'fixture-message', 'synthetic query');
INSERT INTO "portfolio_accounts" ("id", "owner_id", "name", "broker", "market", "base_currency", "is_active", "created_at", "updated_at") VALUES(1, 'fixture-owner', 'Fixture Account', 'fixture-broker', 'cn', 'CNY', 1, '2026-01-05 09:30:00.000000', '2026-01-05 09:30:00.000000');
INSERT INTO "portfolio_cash_ledger" ("id", "account_id", "event_date", "direction", "amount", "currency", "note", "created_at") VALUES(1, 1, '2026-01-05', 'in', 200000.0, 'CNY', 'Synthetic deposit.', '2026-01-05 09:30:00.000000');
INSERT INTO "portfolio_corporate_actions" ("id", "account_id", "symbol", "market", "currency", "effective_date", "action_type", "cash_dividend_per_share", "split_ratio", "note", "created_at") VALUES(1, 1, '600519', 'cn', 'CNY', '2026-01-20', 'cash_dividend', 1.0, NULL, 'Synthetic corporate action.', '2026-01-05 09:30:00.000000');
INSERT INTO "portfolio_daily_snapshots" ("id", "account_id", "snapshot_date", "cost_method", "base_currency", "total_cash", "total_market_value", "total_equity", "unrealized_pnl", "realized_pnl", "fee_total", "tax_total", "fx_stale", "payload", "created_at", "updated_at") VALUES(1, 1, '2026-01-05', 'fifo', 'CNY', 30500.0, 171000.0, 201500.0, 1500.0, 0.0, 5.0, 0.0, 0, '{"fixture":true,"positions":1}', '2026-01-05 15:05:00.000000', '2026-01-05 15:05:00.000000');
INSERT INTO "portfolio_fx_rates" ("id", "from_currency", "to_currency", "rate_date", "rate", "source", "is_stale", "updated_at") VALUES(1, 'CNY', 'CNY', '2026-01-05', 1.0, 'fixture', 0, '2026-01-05 09:30:00.000000');
INSERT INTO "portfolio_position_lots" ("id", "account_id", "cost_method", "symbol", "market", "currency", "open_date", "remaining_quantity", "unit_cost", "source_trade_id", "updated_at") VALUES(1, 1, 'fifo', '600519', 'cn', 'CNY', '2026-01-05', 100.0, 1695.0, 1, '2026-01-05 15:05:00.000000');
INSERT INTO "portfolio_positions" ("id", "account_id", "cost_method", "symbol", "market", "currency", "quantity", "avg_cost", "total_cost", "last_price", "market_value_base", "unrealized_pnl_base", "valuation_currency", "updated_at") VALUES(1, 1, 'fifo', '600519', 'cn', 'CNY', 100.0, 1695.0, 169500.0, 1710.0, 171000.0, 1500.0, 'CNY', '2026-01-05 15:05:00.000000');
INSERT INTO "portfolio_trades" ("id", "account_id", "trade_uid", "symbol", "market", "currency", "trade_date", "side", "quantity", "price", "fee", "tax", "note", "dedup_hash", "created_at") VALUES(1, 1, 'fixture-trade-001', '600519', 'cn', 'CNY', '2026-01-05', 'buy', 100.0, 1695.0, 5.0, 0.0, 'Synthetic buy event.', 'fixture-dedup-001', '2026-01-05 09:30:00.000000');
INSERT INTO "schema_migrations" ("version", "description", "applied_at") VALUES('2026-06-05-create-all-baseline', 'Baseline schema created through SQLAlchemy metadata.create_all', '2026-01-05 09:30:00.000000');
INSERT INTO "stock_daily" ("id", "code", "date", "open", "high", "low", "close", "volume", "amount", "pct_chg", "ma5", "ma10", "ma20", "volume_ratio", "data_source", "created_at", "updated_at") VALUES(1, '600519', '2026-01-05', 1680.0, 1701.0, 1668.0, 1695.0, 1000000.0, 1695000000.0, 1.2, 1688.0, 1675.0, 1650.0, 1.1, 'fixture-provider', '2026-01-05 09:30:00.000000', '2026-01-05 09:30:00.000000');
INSERT INTO "stock_daily" ("id", "code", "date", "open", "high", "low", "close", "volume", "amount", "pct_chg", "ma5", "ma10", "ma20", "volume_ratio", "data_source", "created_at", "updated_at") VALUES(2, '000001', '2026-01-05', 10.1, 10.5, 10.0, 10.4, 2000000.0, 20800000.0, 0.8, 10.2, 10.0, 9.8, 0.9, 'fixture-provider', '2026-01-05 09:30:00.000000', '2026-01-05 09:30:00.000000');
CREATE INDEX ix_agent_provider_turn_bucket ON agent_provider_turns (session_id, provider, model, must_roundtrip);
CREATE INDEX ix_agent_provider_turns_anchor_assistant_message_id ON agent_provider_turns (anchor_assistant_message_id);
CREATE INDEX ix_agent_provider_turns_anchor_user_message_id ON agent_provider_turns (anchor_user_message_id);
CREATE INDEX ix_agent_provider_turns_created_at ON agent_provider_turns (created_at);
CREATE INDEX ix_agent_provider_turns_model ON agent_provider_turns (model);
CREATE INDEX ix_agent_provider_turns_must_roundtrip ON agent_provider_turns (must_roundtrip);
CREATE INDEX ix_agent_provider_turns_provider ON agent_provider_turns (provider);
CREATE INDEX ix_agent_provider_turns_run_id ON agent_provider_turns (run_id);
CREATE INDEX ix_agent_provider_turns_session_id ON agent_provider_turns (session_id);
CREATE INDEX ix_alert_cooldowns_cooldown_until ON alert_cooldowns (cooldown_until);
CREATE INDEX ix_alert_cooldowns_last_triggered_at ON alert_cooldowns (last_triggered_at);
CREATE INDEX ix_alert_cooldowns_rule_id ON alert_cooldowns (rule_id);
CREATE INDEX ix_alert_cooldowns_rule_key ON alert_cooldowns (rule_key);
CREATE INDEX ix_alert_cooldowns_severity ON alert_cooldowns (severity);
CREATE INDEX ix_alert_cooldowns_state ON alert_cooldowns (state);
CREATE INDEX ix_alert_cooldowns_target ON alert_cooldowns (target);
CREATE INDEX ix_alert_cooldowns_updated_at ON alert_cooldowns (updated_at);
CREATE INDEX ix_alert_notification_trigger_channel ON alert_notifications (trigger_id, channel);
CREATE INDEX ix_alert_notifications_channel ON alert_notifications (channel);
CREATE INDEX ix_alert_notifications_created_at ON alert_notifications (created_at);
CREATE INDEX ix_alert_notifications_success ON alert_notifications (success);
CREATE INDEX ix_alert_notifications_trigger_id ON alert_notifications (trigger_id);
CREATE INDEX ix_alert_rule_type_target ON alert_rules (alert_type, target);
CREATE INDEX ix_alert_rules_alert_type ON alert_rules (alert_type);
CREATE INDEX ix_alert_rules_created_at ON alert_rules (created_at);
CREATE INDEX ix_alert_rules_enabled ON alert_rules (enabled);
CREATE INDEX ix_alert_rules_severity ON alert_rules (severity);
CREATE INDEX ix_alert_rules_source ON alert_rules (source);
CREATE INDEX ix_alert_rules_target ON alert_rules (target);
CREATE INDEX ix_alert_rules_target_scope ON alert_rules (target_scope);
CREATE INDEX ix_alert_rules_updated_at ON alert_rules (updated_at);
CREATE INDEX ix_alert_trigger_rule_time ON alert_triggers (rule_id, triggered_at);
CREATE INDEX ix_alert_triggers_data_timestamp ON alert_triggers (data_timestamp);
CREATE INDEX ix_alert_triggers_rule_id ON alert_triggers (rule_id);
CREATE INDEX ix_alert_triggers_status ON alert_triggers (status);
CREATE INDEX ix_alert_triggers_target ON alert_triggers (target);
CREATE INDEX ix_alert_triggers_triggered_at ON alert_triggers (triggered_at);
CREATE INDEX ix_analysis_code_time ON analysis_history (code, created_at);
CREATE INDEX ix_analysis_history_code ON analysis_history (code);
CREATE INDEX ix_analysis_history_created_at ON analysis_history (created_at);
CREATE INDEX ix_analysis_history_query_id ON analysis_history (query_id);
CREATE INDEX ix_analysis_history_report_type ON analysis_history (report_type);
CREATE INDEX ix_backtest_code_date ON backtest_results (code, analysis_date);
CREATE INDEX ix_backtest_results_analysis_date ON backtest_results (analysis_date);
CREATE INDEX ix_backtest_results_analysis_history_id ON backtest_results (analysis_history_id);
CREATE INDEX ix_backtest_results_code ON backtest_results (code);
CREATE INDEX ix_backtest_results_evaluated_at ON backtest_results (evaluated_at);
CREATE INDEX ix_backtest_summaries_code ON backtest_summaries (code);
CREATE INDEX ix_backtest_summaries_computed_at ON backtest_summaries (computed_at);
CREATE INDEX ix_backtest_summaries_scope ON backtest_summaries (scope);
CREATE INDEX ix_code_date ON stock_daily (code, date);
CREATE INDEX ix_conversation_messages_created_at ON conversation_messages (created_at);
CREATE INDEX ix_conversation_messages_session_id ON conversation_messages (session_id);
CREATE INDEX ix_conversation_summaries_created_at ON conversation_summaries (created_at);
CREATE UNIQUE INDEX ix_conversation_summaries_session_id ON conversation_summaries (session_id);
CREATE INDEX ix_conversation_summaries_updated_at ON conversation_summaries (updated_at);
CREATE INDEX ix_decision_signal_feedback_created_at ON decision_signal_feedback (created_at);
CREATE INDEX ix_decision_signal_feedback_feedback_value ON decision_signal_feedback (feedback_value);
CREATE INDEX ix_decision_signal_feedback_reason_code ON decision_signal_feedback (reason_code);
CREATE UNIQUE INDEX ix_decision_signal_feedback_signal_id ON decision_signal_feedback (signal_id);
CREATE INDEX ix_decision_signal_feedback_source ON decision_signal_feedback (source);
CREATE INDEX ix_decision_signal_feedback_updated_at ON decision_signal_feedback (updated_at);
CREATE INDEX ix_decision_signal_market_status_time ON decision_signals (market, status, created_at);
CREATE INDEX ix_decision_signal_market_stock_profile_created ON decision_signals (market, stock_code, decision_profile, created_at);
CREATE INDEX ix_decision_signal_outcome_stats_action ON decision_signal_outcomes (engine_version, action, horizon);
CREATE INDEX ix_decision_signal_outcome_stats_market ON decision_signal_outcomes (engine_version, market, horizon);
CREATE INDEX ix_decision_signal_outcomes_action ON decision_signal_outcomes (action);
CREATE INDEX ix_decision_signal_outcomes_anchor_date ON decision_signal_outcomes (anchor_date);
CREATE INDEX ix_decision_signal_outcomes_created_at ON decision_signal_outcomes (created_at);
CREATE INDEX ix_decision_signal_outcomes_data_quality_level ON decision_signal_outcomes (data_quality_level);
CREATE INDEX ix_decision_signal_outcomes_direction_expected ON decision_signal_outcomes (direction_expected);
CREATE INDEX ix_decision_signal_outcomes_engine_version ON decision_signal_outcomes (engine_version);
CREATE INDEX ix_decision_signal_outcomes_eval_status ON decision_signal_outcomes (eval_status);
CREATE INDEX ix_decision_signal_outcomes_holding_state ON decision_signal_outcomes (holding_state);
CREATE INDEX ix_decision_signal_outcomes_horizon ON decision_signal_outcomes (horizon);
CREATE INDEX ix_decision_signal_outcomes_market ON decision_signal_outcomes (market);
CREATE INDEX ix_decision_signal_outcomes_market_phase ON decision_signal_outcomes (market_phase);
CREATE INDEX ix_decision_signal_outcomes_outcome ON decision_signal_outcomes (outcome);
CREATE INDEX ix_decision_signal_outcomes_plan_quality ON decision_signal_outcomes (plan_quality);
CREATE INDEX ix_decision_signal_outcomes_signal_id ON decision_signal_outcomes (signal_id);
CREATE INDEX ix_decision_signal_outcomes_source_agent ON decision_signal_outcomes (source_agent);
CREATE INDEX ix_decision_signal_outcomes_source_type ON decision_signal_outcomes (source_type);
CREATE INDEX ix_decision_signal_outcomes_unable_reason ON decision_signal_outcomes (unable_reason);
CREATE INDEX ix_decision_signal_outcomes_updated_at ON decision_signal_outcomes (updated_at);
CREATE INDEX ix_decision_signal_report_type_market_stock_action_horizon_phase ON decision_signals (source_report_id, source_type, market, stock_code, action, horizon, market_phase);
CREATE INDEX ix_decision_signal_report_type_market_stock_profile_action_horizon_phase ON decision_signals (source_report_id, source_type, market, stock_code, decision_profile, action, horizon, market_phase);
CREATE INDEX ix_decision_signal_stock_status_time ON decision_signals (stock_code, status, created_at);
CREATE INDEX ix_decision_signal_trace_type_market_stock_action_horizon_phase ON decision_signals (trace_id, source_type, market, stock_code, action, horizon, market_phase);
CREATE INDEX ix_decision_signal_trace_type_market_stock_profile_action_horizon_phase ON decision_signals (trace_id, source_type, market, stock_code, decision_profile, action, horizon, market_phase);
CREATE INDEX ix_decision_signals_action ON decision_signals (action);
CREATE INDEX ix_decision_signals_created_at ON decision_signals (created_at);
CREATE INDEX ix_decision_signals_decision_profile ON decision_signals (decision_profile);
CREATE INDEX ix_decision_signals_expires_at ON decision_signals (expires_at);
CREATE INDEX ix_decision_signals_horizon ON decision_signals (horizon);
CREATE INDEX ix_decision_signals_market ON decision_signals (market);
CREATE INDEX ix_decision_signals_market_phase ON decision_signals (market_phase);
CREATE INDEX ix_decision_signals_plan_quality ON decision_signals (plan_quality);
CREATE INDEX ix_decision_signals_source_report_id ON decision_signals (source_report_id);
CREATE INDEX ix_decision_signals_source_type ON decision_signals (source_type);
CREATE INDEX ix_decision_signals_status ON decision_signals (status);
CREATE INDEX ix_decision_signals_stock_code ON decision_signals (stock_code);
CREATE INDEX ix_decision_signals_trace_id ON decision_signals (trace_id);
CREATE INDEX ix_decision_signals_trigger_source ON decision_signals (trigger_source);
CREATE INDEX ix_decision_signals_updated_at ON decision_signals (updated_at);
CREATE INDEX ix_fundamental_snapshot_code ON fundamental_snapshot (code);
CREATE INDEX ix_fundamental_snapshot_created ON fundamental_snapshot (created_at);
CREATE INDEX ix_fundamental_snapshot_created_at ON fundamental_snapshot (created_at);
CREATE INDEX ix_fundamental_snapshot_query_code ON fundamental_snapshot (query_id, code);
CREATE INDEX ix_fundamental_snapshot_query_id ON fundamental_snapshot (query_id);
CREATE INDEX ix_intel_item_fetch_time ON intelligence_items (fetched_at);
CREATE INDEX ix_intel_item_scope_time ON intelligence_items (scope_type, scope_value, market, published_at);
CREATE INDEX ix_intel_source_scope ON intelligence_sources (scope_type, scope_value, market);
CREATE INDEX ix_intelligence_items_fetched_at ON intelligence_items (fetched_at);
CREATE INDEX ix_intelligence_items_market ON intelligence_items (market);
CREATE INDEX ix_intelligence_items_published_at ON intelligence_items (published_at);
CREATE INDEX ix_intelligence_items_scope_type ON intelligence_items (scope_type);
CREATE INDEX ix_intelligence_items_scope_value ON intelligence_items (scope_value);
CREATE INDEX ix_intelligence_items_source_id ON intelligence_items (source_id);
CREATE INDEX ix_intelligence_items_source_name ON intelligence_items (source_name);
CREATE INDEX ix_intelligence_items_source_type ON intelligence_items (source_type);
CREATE INDEX ix_intelligence_items_url ON intelligence_items (url);
CREATE INDEX ix_intelligence_sources_created_at ON intelligence_sources (created_at);
CREATE INDEX ix_intelligence_sources_enabled ON intelligence_sources (enabled);
CREATE INDEX ix_intelligence_sources_last_fetched_at ON intelligence_sources (last_fetched_at);
CREATE INDEX ix_intelligence_sources_market ON intelligence_sources (market);
CREATE UNIQUE INDEX ix_intelligence_sources_name ON intelligence_sources (name);
CREATE INDEX ix_intelligence_sources_scope_type ON intelligence_sources (scope_type);
CREATE INDEX ix_intelligence_sources_scope_value ON intelligence_sources (scope_value);
CREATE INDEX ix_intelligence_sources_source_type ON intelligence_sources (source_type);
CREATE INDEX ix_intelligence_sources_updated_at ON intelligence_sources (updated_at);
CREATE INDEX ix_llm_usage_call_type ON llm_usage (call_type);
CREATE INDEX ix_llm_usage_called_at ON llm_usage (called_at);
CREATE INDEX ix_news_code_pub ON news_intel (code, published_date);
CREATE INDEX ix_news_intel_code ON news_intel (code);
CREATE INDEX ix_news_intel_dimension ON news_intel (dimension);
CREATE INDEX ix_news_intel_fetched_at ON news_intel (fetched_at);
CREATE INDEX ix_news_intel_provider ON news_intel (provider);
CREATE INDEX ix_news_intel_published_date ON news_intel (published_date);
CREATE INDEX ix_news_intel_query_id ON news_intel (query_id);
CREATE INDEX ix_news_intel_query_source ON news_intel (query_source);
CREATE INDEX ix_portfolio_account_owner_active ON portfolio_accounts (owner_id, is_active);
CREATE INDEX ix_portfolio_accounts_created_at ON portfolio_accounts (created_at);
CREATE INDEX ix_portfolio_accounts_is_active ON portfolio_accounts (is_active);
CREATE INDEX ix_portfolio_accounts_market ON portfolio_accounts (market);
CREATE INDEX ix_portfolio_accounts_owner_id ON portfolio_accounts (owner_id);
CREATE INDEX ix_portfolio_ca_account_date ON portfolio_corporate_actions (account_id, effective_date);
CREATE INDEX ix_portfolio_cash_account_date ON portfolio_cash_ledger (account_id, event_date);
CREATE INDEX ix_portfolio_cash_ledger_account_id ON portfolio_cash_ledger (account_id);
CREATE INDEX ix_portfolio_cash_ledger_created_at ON portfolio_cash_ledger (created_at);
CREATE INDEX ix_portfolio_cash_ledger_event_date ON portfolio_cash_ledger (event_date);
CREATE INDEX ix_portfolio_corporate_actions_account_id ON portfolio_corporate_actions (account_id);
CREATE INDEX ix_portfolio_corporate_actions_created_at ON portfolio_corporate_actions (created_at);
CREATE INDEX ix_portfolio_corporate_actions_effective_date ON portfolio_corporate_actions (effective_date);
CREATE INDEX ix_portfolio_corporate_actions_symbol ON portfolio_corporate_actions (symbol);
CREATE INDEX ix_portfolio_daily_snapshots_account_id ON portfolio_daily_snapshots (account_id);
CREATE INDEX ix_portfolio_daily_snapshots_created_at ON portfolio_daily_snapshots (created_at);
CREATE INDEX ix_portfolio_daily_snapshots_snapshot_date ON portfolio_daily_snapshots (snapshot_date);
CREATE INDEX ix_portfolio_fx_rates_from_currency ON portfolio_fx_rates (from_currency);
CREATE INDEX ix_portfolio_fx_rates_rate_date ON portfolio_fx_rates (rate_date);
CREATE INDEX ix_portfolio_fx_rates_to_currency ON portfolio_fx_rates (to_currency);
CREATE INDEX ix_portfolio_lot_account_symbol ON portfolio_position_lots (account_id, symbol);
CREATE INDEX ix_portfolio_position_lots_account_id ON portfolio_position_lots (account_id);
CREATE INDEX ix_portfolio_position_lots_open_date ON portfolio_position_lots (open_date);
CREATE INDEX ix_portfolio_position_lots_symbol ON portfolio_position_lots (symbol);
CREATE INDEX ix_portfolio_position_lots_updated_at ON portfolio_position_lots (updated_at);
CREATE INDEX ix_portfolio_positions_account_id ON portfolio_positions (account_id);
CREATE INDEX ix_portfolio_positions_symbol ON portfolio_positions (symbol);
CREATE INDEX ix_portfolio_positions_updated_at ON portfolio_positions (updated_at);
CREATE INDEX ix_portfolio_trade_account_date ON portfolio_trades (account_id, trade_date);
CREATE INDEX ix_portfolio_trades_account_id ON portfolio_trades (account_id);
CREATE INDEX ix_portfolio_trades_created_at ON portfolio_trades (created_at);
CREATE INDEX ix_portfolio_trades_dedup_hash ON portfolio_trades (dedup_hash);
CREATE INDEX ix_portfolio_trades_symbol ON portfolio_trades (symbol);
CREATE INDEX ix_portfolio_trades_trade_date ON portfolio_trades (trade_date);
CREATE INDEX ix_schema_migrations_applied_at ON schema_migrations (applied_at);
CREATE INDEX ix_stock_daily_code ON stock_daily (code);
CREATE INDEX ix_stock_daily_date ON stock_daily (date);
COMMIT;
PRAGMA foreign_keys=ON;
