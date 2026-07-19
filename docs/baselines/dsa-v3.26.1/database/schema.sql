-- table: agent_provider_turns
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

-- table: alert_cooldowns
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

-- table: alert_notifications
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

-- table: alert_rules
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

-- table: alert_triggers
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

-- table: analysis_history
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

-- table: backtest_results
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

-- table: backtest_summaries
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

-- table: conversation_messages
CREATE TABLE conversation_messages (
	id INTEGER NOT NULL,
	session_id VARCHAR(100) NOT NULL,
	role VARCHAR(20) NOT NULL,
	content TEXT NOT NULL,
	created_at DATETIME,
	PRIMARY KEY (id)
);

-- table: conversation_summaries
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

-- table: decision_signal_feedback
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

-- table: decision_signal_outcomes
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

-- table: decision_signals
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

-- table: fundamental_snapshot
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

-- table: intelligence_items
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

-- table: intelligence_sources
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

-- table: llm_usage
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

-- table: news_intel
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

-- table: portfolio_accounts
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

-- table: portfolio_cash_ledger
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

-- table: portfolio_corporate_actions
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

-- table: portfolio_daily_snapshots
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

-- table: portfolio_fx_rates
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

-- table: portfolio_position_lots
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

-- table: portfolio_positions
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

-- table: portfolio_trades
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

-- table: schema_migrations
CREATE TABLE schema_migrations (
	version VARCHAR(64) NOT NULL,
	description VARCHAR(255) NOT NULL,
	applied_at DATETIME NOT NULL,
	PRIMARY KEY (version)
);

-- table: stock_daily
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

-- index: ix_agent_provider_turn_bucket
CREATE INDEX ix_agent_provider_turn_bucket ON agent_provider_turns (session_id, provider, model, must_roundtrip);

-- index: ix_agent_provider_turns_anchor_assistant_message_id
CREATE INDEX ix_agent_provider_turns_anchor_assistant_message_id ON agent_provider_turns (anchor_assistant_message_id);

-- index: ix_agent_provider_turns_anchor_user_message_id
CREATE INDEX ix_agent_provider_turns_anchor_user_message_id ON agent_provider_turns (anchor_user_message_id);

-- index: ix_agent_provider_turns_created_at
CREATE INDEX ix_agent_provider_turns_created_at ON agent_provider_turns (created_at);

-- index: ix_agent_provider_turns_model
CREATE INDEX ix_agent_provider_turns_model ON agent_provider_turns (model);

-- index: ix_agent_provider_turns_must_roundtrip
CREATE INDEX ix_agent_provider_turns_must_roundtrip ON agent_provider_turns (must_roundtrip);

-- index: ix_agent_provider_turns_provider
CREATE INDEX ix_agent_provider_turns_provider ON agent_provider_turns (provider);

-- index: ix_agent_provider_turns_run_id
CREATE INDEX ix_agent_provider_turns_run_id ON agent_provider_turns (run_id);

-- index: ix_agent_provider_turns_session_id
CREATE INDEX ix_agent_provider_turns_session_id ON agent_provider_turns (session_id);

-- index: ix_alert_cooldowns_cooldown_until
CREATE INDEX ix_alert_cooldowns_cooldown_until ON alert_cooldowns (cooldown_until);

-- index: ix_alert_cooldowns_last_triggered_at
CREATE INDEX ix_alert_cooldowns_last_triggered_at ON alert_cooldowns (last_triggered_at);

-- index: ix_alert_cooldowns_rule_id
CREATE INDEX ix_alert_cooldowns_rule_id ON alert_cooldowns (rule_id);

-- index: ix_alert_cooldowns_rule_key
CREATE INDEX ix_alert_cooldowns_rule_key ON alert_cooldowns (rule_key);

-- index: ix_alert_cooldowns_severity
CREATE INDEX ix_alert_cooldowns_severity ON alert_cooldowns (severity);

-- index: ix_alert_cooldowns_state
CREATE INDEX ix_alert_cooldowns_state ON alert_cooldowns (state);

-- index: ix_alert_cooldowns_target
CREATE INDEX ix_alert_cooldowns_target ON alert_cooldowns (target);

-- index: ix_alert_cooldowns_updated_at
CREATE INDEX ix_alert_cooldowns_updated_at ON alert_cooldowns (updated_at);

-- index: ix_alert_notification_trigger_channel
CREATE INDEX ix_alert_notification_trigger_channel ON alert_notifications (trigger_id, channel);

-- index: ix_alert_notifications_channel
CREATE INDEX ix_alert_notifications_channel ON alert_notifications (channel);

-- index: ix_alert_notifications_created_at
CREATE INDEX ix_alert_notifications_created_at ON alert_notifications (created_at);

-- index: ix_alert_notifications_success
CREATE INDEX ix_alert_notifications_success ON alert_notifications (success);

-- index: ix_alert_notifications_trigger_id
CREATE INDEX ix_alert_notifications_trigger_id ON alert_notifications (trigger_id);

-- index: ix_alert_rule_type_target
CREATE INDEX ix_alert_rule_type_target ON alert_rules (alert_type, target);

-- index: ix_alert_rules_alert_type
CREATE INDEX ix_alert_rules_alert_type ON alert_rules (alert_type);

-- index: ix_alert_rules_created_at
CREATE INDEX ix_alert_rules_created_at ON alert_rules (created_at);

-- index: ix_alert_rules_enabled
CREATE INDEX ix_alert_rules_enabled ON alert_rules (enabled);

-- index: ix_alert_rules_severity
CREATE INDEX ix_alert_rules_severity ON alert_rules (severity);

-- index: ix_alert_rules_source
CREATE INDEX ix_alert_rules_source ON alert_rules (source);

-- index: ix_alert_rules_target
CREATE INDEX ix_alert_rules_target ON alert_rules (target);

-- index: ix_alert_rules_target_scope
CREATE INDEX ix_alert_rules_target_scope ON alert_rules (target_scope);

-- index: ix_alert_rules_updated_at
CREATE INDEX ix_alert_rules_updated_at ON alert_rules (updated_at);

-- index: ix_alert_trigger_rule_time
CREATE INDEX ix_alert_trigger_rule_time ON alert_triggers (rule_id, triggered_at);

-- index: ix_alert_triggers_data_timestamp
CREATE INDEX ix_alert_triggers_data_timestamp ON alert_triggers (data_timestamp);

-- index: ix_alert_triggers_rule_id
CREATE INDEX ix_alert_triggers_rule_id ON alert_triggers (rule_id);

-- index: ix_alert_triggers_status
CREATE INDEX ix_alert_triggers_status ON alert_triggers (status);

-- index: ix_alert_triggers_target
CREATE INDEX ix_alert_triggers_target ON alert_triggers (target);

-- index: ix_alert_triggers_triggered_at
CREATE INDEX ix_alert_triggers_triggered_at ON alert_triggers (triggered_at);

-- index: ix_analysis_code_time
CREATE INDEX ix_analysis_code_time ON analysis_history (code, created_at);

-- index: ix_analysis_history_code
CREATE INDEX ix_analysis_history_code ON analysis_history (code);

-- index: ix_analysis_history_created_at
CREATE INDEX ix_analysis_history_created_at ON analysis_history (created_at);

-- index: ix_analysis_history_query_id
CREATE INDEX ix_analysis_history_query_id ON analysis_history (query_id);

-- index: ix_analysis_history_report_type
CREATE INDEX ix_analysis_history_report_type ON analysis_history (report_type);

-- index: ix_backtest_code_date
CREATE INDEX ix_backtest_code_date ON backtest_results (code, analysis_date);

-- index: ix_backtest_results_analysis_date
CREATE INDEX ix_backtest_results_analysis_date ON backtest_results (analysis_date);

-- index: ix_backtest_results_analysis_history_id
CREATE INDEX ix_backtest_results_analysis_history_id ON backtest_results (analysis_history_id);

-- index: ix_backtest_results_code
CREATE INDEX ix_backtest_results_code ON backtest_results (code);

-- index: ix_backtest_results_evaluated_at
CREATE INDEX ix_backtest_results_evaluated_at ON backtest_results (evaluated_at);

-- index: ix_backtest_summaries_code
CREATE INDEX ix_backtest_summaries_code ON backtest_summaries (code);

-- index: ix_backtest_summaries_computed_at
CREATE INDEX ix_backtest_summaries_computed_at ON backtest_summaries (computed_at);

-- index: ix_backtest_summaries_scope
CREATE INDEX ix_backtest_summaries_scope ON backtest_summaries (scope);

-- index: ix_code_date
CREATE INDEX ix_code_date ON stock_daily (code, date);

-- index: ix_conversation_messages_created_at
CREATE INDEX ix_conversation_messages_created_at ON conversation_messages (created_at);

-- index: ix_conversation_messages_session_id
CREATE INDEX ix_conversation_messages_session_id ON conversation_messages (session_id);

-- index: ix_conversation_summaries_created_at
CREATE INDEX ix_conversation_summaries_created_at ON conversation_summaries (created_at);

-- index: ix_conversation_summaries_session_id
CREATE UNIQUE INDEX ix_conversation_summaries_session_id ON conversation_summaries (session_id);

-- index: ix_conversation_summaries_updated_at
CREATE INDEX ix_conversation_summaries_updated_at ON conversation_summaries (updated_at);

-- index: ix_decision_signal_feedback_created_at
CREATE INDEX ix_decision_signal_feedback_created_at ON decision_signal_feedback (created_at);

-- index: ix_decision_signal_feedback_feedback_value
CREATE INDEX ix_decision_signal_feedback_feedback_value ON decision_signal_feedback (feedback_value);

-- index: ix_decision_signal_feedback_reason_code
CREATE INDEX ix_decision_signal_feedback_reason_code ON decision_signal_feedback (reason_code);

-- index: ix_decision_signal_feedback_signal_id
CREATE UNIQUE INDEX ix_decision_signal_feedback_signal_id ON decision_signal_feedback (signal_id);

-- index: ix_decision_signal_feedback_source
CREATE INDEX ix_decision_signal_feedback_source ON decision_signal_feedback (source);

-- index: ix_decision_signal_feedback_updated_at
CREATE INDEX ix_decision_signal_feedback_updated_at ON decision_signal_feedback (updated_at);

-- index: ix_decision_signal_market_status_time
CREATE INDEX ix_decision_signal_market_status_time ON decision_signals (market, status, created_at);

-- index: ix_decision_signal_market_stock_profile_created
CREATE INDEX ix_decision_signal_market_stock_profile_created ON decision_signals (market, stock_code, decision_profile, created_at);

-- index: ix_decision_signal_outcome_stats_action
CREATE INDEX ix_decision_signal_outcome_stats_action ON decision_signal_outcomes (engine_version, action, horizon);

-- index: ix_decision_signal_outcome_stats_market
CREATE INDEX ix_decision_signal_outcome_stats_market ON decision_signal_outcomes (engine_version, market, horizon);

-- index: ix_decision_signal_outcomes_action
CREATE INDEX ix_decision_signal_outcomes_action ON decision_signal_outcomes (action);

-- index: ix_decision_signal_outcomes_anchor_date
CREATE INDEX ix_decision_signal_outcomes_anchor_date ON decision_signal_outcomes (anchor_date);

-- index: ix_decision_signal_outcomes_created_at
CREATE INDEX ix_decision_signal_outcomes_created_at ON decision_signal_outcomes (created_at);

-- index: ix_decision_signal_outcomes_data_quality_level
CREATE INDEX ix_decision_signal_outcomes_data_quality_level ON decision_signal_outcomes (data_quality_level);

-- index: ix_decision_signal_outcomes_direction_expected
CREATE INDEX ix_decision_signal_outcomes_direction_expected ON decision_signal_outcomes (direction_expected);

-- index: ix_decision_signal_outcomes_engine_version
CREATE INDEX ix_decision_signal_outcomes_engine_version ON decision_signal_outcomes (engine_version);

-- index: ix_decision_signal_outcomes_eval_status
CREATE INDEX ix_decision_signal_outcomes_eval_status ON decision_signal_outcomes (eval_status);

-- index: ix_decision_signal_outcomes_holding_state
CREATE INDEX ix_decision_signal_outcomes_holding_state ON decision_signal_outcomes (holding_state);

-- index: ix_decision_signal_outcomes_horizon
CREATE INDEX ix_decision_signal_outcomes_horizon ON decision_signal_outcomes (horizon);

-- index: ix_decision_signal_outcomes_market
CREATE INDEX ix_decision_signal_outcomes_market ON decision_signal_outcomes (market);

-- index: ix_decision_signal_outcomes_market_phase
CREATE INDEX ix_decision_signal_outcomes_market_phase ON decision_signal_outcomes (market_phase);

-- index: ix_decision_signal_outcomes_outcome
CREATE INDEX ix_decision_signal_outcomes_outcome ON decision_signal_outcomes (outcome);

-- index: ix_decision_signal_outcomes_plan_quality
CREATE INDEX ix_decision_signal_outcomes_plan_quality ON decision_signal_outcomes (plan_quality);

-- index: ix_decision_signal_outcomes_signal_id
CREATE INDEX ix_decision_signal_outcomes_signal_id ON decision_signal_outcomes (signal_id);

-- index: ix_decision_signal_outcomes_source_agent
CREATE INDEX ix_decision_signal_outcomes_source_agent ON decision_signal_outcomes (source_agent);

-- index: ix_decision_signal_outcomes_source_type
CREATE INDEX ix_decision_signal_outcomes_source_type ON decision_signal_outcomes (source_type);

-- index: ix_decision_signal_outcomes_unable_reason
CREATE INDEX ix_decision_signal_outcomes_unable_reason ON decision_signal_outcomes (unable_reason);

-- index: ix_decision_signal_outcomes_updated_at
CREATE INDEX ix_decision_signal_outcomes_updated_at ON decision_signal_outcomes (updated_at);

-- index: ix_decision_signal_report_type_market_stock_action_horizon_phase
CREATE INDEX ix_decision_signal_report_type_market_stock_action_horizon_phase ON decision_signals (source_report_id, source_type, market, stock_code, action, horizon, market_phase);

-- index: ix_decision_signal_report_type_market_stock_profile_action_horizon_phase
CREATE INDEX ix_decision_signal_report_type_market_stock_profile_action_horizon_phase ON decision_signals (source_report_id, source_type, market, stock_code, decision_profile, action, horizon, market_phase);

-- index: ix_decision_signal_stock_status_time
CREATE INDEX ix_decision_signal_stock_status_time ON decision_signals (stock_code, status, created_at);

-- index: ix_decision_signal_trace_type_market_stock_action_horizon_phase
CREATE INDEX ix_decision_signal_trace_type_market_stock_action_horizon_phase ON decision_signals (trace_id, source_type, market, stock_code, action, horizon, market_phase);

-- index: ix_decision_signal_trace_type_market_stock_profile_action_horizon_phase
CREATE INDEX ix_decision_signal_trace_type_market_stock_profile_action_horizon_phase ON decision_signals (trace_id, source_type, market, stock_code, decision_profile, action, horizon, market_phase);

-- index: ix_decision_signals_action
CREATE INDEX ix_decision_signals_action ON decision_signals (action);

-- index: ix_decision_signals_created_at
CREATE INDEX ix_decision_signals_created_at ON decision_signals (created_at);

-- index: ix_decision_signals_decision_profile
CREATE INDEX ix_decision_signals_decision_profile ON decision_signals (decision_profile);

-- index: ix_decision_signals_expires_at
CREATE INDEX ix_decision_signals_expires_at ON decision_signals (expires_at);

-- index: ix_decision_signals_horizon
CREATE INDEX ix_decision_signals_horizon ON decision_signals (horizon);

-- index: ix_decision_signals_market
CREATE INDEX ix_decision_signals_market ON decision_signals (market);

-- index: ix_decision_signals_market_phase
CREATE INDEX ix_decision_signals_market_phase ON decision_signals (market_phase);

-- index: ix_decision_signals_plan_quality
CREATE INDEX ix_decision_signals_plan_quality ON decision_signals (plan_quality);

-- index: ix_decision_signals_source_report_id
CREATE INDEX ix_decision_signals_source_report_id ON decision_signals (source_report_id);

-- index: ix_decision_signals_source_type
CREATE INDEX ix_decision_signals_source_type ON decision_signals (source_type);

-- index: ix_decision_signals_status
CREATE INDEX ix_decision_signals_status ON decision_signals (status);

-- index: ix_decision_signals_stock_code
CREATE INDEX ix_decision_signals_stock_code ON decision_signals (stock_code);

-- index: ix_decision_signals_trace_id
CREATE INDEX ix_decision_signals_trace_id ON decision_signals (trace_id);

-- index: ix_decision_signals_trigger_source
CREATE INDEX ix_decision_signals_trigger_source ON decision_signals (trigger_source);

-- index: ix_decision_signals_updated_at
CREATE INDEX ix_decision_signals_updated_at ON decision_signals (updated_at);

-- index: ix_fundamental_snapshot_code
CREATE INDEX ix_fundamental_snapshot_code ON fundamental_snapshot (code);

-- index: ix_fundamental_snapshot_created
CREATE INDEX ix_fundamental_snapshot_created ON fundamental_snapshot (created_at);

-- index: ix_fundamental_snapshot_created_at
CREATE INDEX ix_fundamental_snapshot_created_at ON fundamental_snapshot (created_at);

-- index: ix_fundamental_snapshot_query_code
CREATE INDEX ix_fundamental_snapshot_query_code ON fundamental_snapshot (query_id, code);

-- index: ix_fundamental_snapshot_query_id
CREATE INDEX ix_fundamental_snapshot_query_id ON fundamental_snapshot (query_id);

-- index: ix_intel_item_fetch_time
CREATE INDEX ix_intel_item_fetch_time ON intelligence_items (fetched_at);

-- index: ix_intel_item_scope_time
CREATE INDEX ix_intel_item_scope_time ON intelligence_items (scope_type, scope_value, market, published_at);

-- index: ix_intel_source_scope
CREATE INDEX ix_intel_source_scope ON intelligence_sources (scope_type, scope_value, market);

-- index: ix_intelligence_items_fetched_at
CREATE INDEX ix_intelligence_items_fetched_at ON intelligence_items (fetched_at);

-- index: ix_intelligence_items_market
CREATE INDEX ix_intelligence_items_market ON intelligence_items (market);

-- index: ix_intelligence_items_published_at
CREATE INDEX ix_intelligence_items_published_at ON intelligence_items (published_at);

-- index: ix_intelligence_items_scope_type
CREATE INDEX ix_intelligence_items_scope_type ON intelligence_items (scope_type);

-- index: ix_intelligence_items_scope_value
CREATE INDEX ix_intelligence_items_scope_value ON intelligence_items (scope_value);

-- index: ix_intelligence_items_source_id
CREATE INDEX ix_intelligence_items_source_id ON intelligence_items (source_id);

-- index: ix_intelligence_items_source_name
CREATE INDEX ix_intelligence_items_source_name ON intelligence_items (source_name);

-- index: ix_intelligence_items_source_type
CREATE INDEX ix_intelligence_items_source_type ON intelligence_items (source_type);

-- index: ix_intelligence_items_url
CREATE INDEX ix_intelligence_items_url ON intelligence_items (url);

-- index: ix_intelligence_sources_created_at
CREATE INDEX ix_intelligence_sources_created_at ON intelligence_sources (created_at);

-- index: ix_intelligence_sources_enabled
CREATE INDEX ix_intelligence_sources_enabled ON intelligence_sources (enabled);

-- index: ix_intelligence_sources_last_fetched_at
CREATE INDEX ix_intelligence_sources_last_fetched_at ON intelligence_sources (last_fetched_at);

-- index: ix_intelligence_sources_market
CREATE INDEX ix_intelligence_sources_market ON intelligence_sources (market);

-- index: ix_intelligence_sources_name
CREATE UNIQUE INDEX ix_intelligence_sources_name ON intelligence_sources (name);

-- index: ix_intelligence_sources_scope_type
CREATE INDEX ix_intelligence_sources_scope_type ON intelligence_sources (scope_type);

-- index: ix_intelligence_sources_scope_value
CREATE INDEX ix_intelligence_sources_scope_value ON intelligence_sources (scope_value);

-- index: ix_intelligence_sources_source_type
CREATE INDEX ix_intelligence_sources_source_type ON intelligence_sources (source_type);

-- index: ix_intelligence_sources_updated_at
CREATE INDEX ix_intelligence_sources_updated_at ON intelligence_sources (updated_at);

-- index: ix_llm_usage_call_type
CREATE INDEX ix_llm_usage_call_type ON llm_usage (call_type);

-- index: ix_llm_usage_called_at
CREATE INDEX ix_llm_usage_called_at ON llm_usage (called_at);

-- index: ix_news_code_pub
CREATE INDEX ix_news_code_pub ON news_intel (code, published_date);

-- index: ix_news_intel_code
CREATE INDEX ix_news_intel_code ON news_intel (code);

-- index: ix_news_intel_dimension
CREATE INDEX ix_news_intel_dimension ON news_intel (dimension);

-- index: ix_news_intel_fetched_at
CREATE INDEX ix_news_intel_fetched_at ON news_intel (fetched_at);

-- index: ix_news_intel_provider
CREATE INDEX ix_news_intel_provider ON news_intel (provider);

-- index: ix_news_intel_published_date
CREATE INDEX ix_news_intel_published_date ON news_intel (published_date);

-- index: ix_news_intel_query_id
CREATE INDEX ix_news_intel_query_id ON news_intel (query_id);

-- index: ix_news_intel_query_source
CREATE INDEX ix_news_intel_query_source ON news_intel (query_source);

-- index: ix_portfolio_account_owner_active
CREATE INDEX ix_portfolio_account_owner_active ON portfolio_accounts (owner_id, is_active);

-- index: ix_portfolio_accounts_created_at
CREATE INDEX ix_portfolio_accounts_created_at ON portfolio_accounts (created_at);

-- index: ix_portfolio_accounts_is_active
CREATE INDEX ix_portfolio_accounts_is_active ON portfolio_accounts (is_active);

-- index: ix_portfolio_accounts_market
CREATE INDEX ix_portfolio_accounts_market ON portfolio_accounts (market);

-- index: ix_portfolio_accounts_owner_id
CREATE INDEX ix_portfolio_accounts_owner_id ON portfolio_accounts (owner_id);

-- index: ix_portfolio_ca_account_date
CREATE INDEX ix_portfolio_ca_account_date ON portfolio_corporate_actions (account_id, effective_date);

-- index: ix_portfolio_cash_account_date
CREATE INDEX ix_portfolio_cash_account_date ON portfolio_cash_ledger (account_id, event_date);

-- index: ix_portfolio_cash_ledger_account_id
CREATE INDEX ix_portfolio_cash_ledger_account_id ON portfolio_cash_ledger (account_id);

-- index: ix_portfolio_cash_ledger_created_at
CREATE INDEX ix_portfolio_cash_ledger_created_at ON portfolio_cash_ledger (created_at);

-- index: ix_portfolio_cash_ledger_event_date
CREATE INDEX ix_portfolio_cash_ledger_event_date ON portfolio_cash_ledger (event_date);

-- index: ix_portfolio_corporate_actions_account_id
CREATE INDEX ix_portfolio_corporate_actions_account_id ON portfolio_corporate_actions (account_id);

-- index: ix_portfolio_corporate_actions_created_at
CREATE INDEX ix_portfolio_corporate_actions_created_at ON portfolio_corporate_actions (created_at);

-- index: ix_portfolio_corporate_actions_effective_date
CREATE INDEX ix_portfolio_corporate_actions_effective_date ON portfolio_corporate_actions (effective_date);

-- index: ix_portfolio_corporate_actions_symbol
CREATE INDEX ix_portfolio_corporate_actions_symbol ON portfolio_corporate_actions (symbol);

-- index: ix_portfolio_daily_snapshots_account_id
CREATE INDEX ix_portfolio_daily_snapshots_account_id ON portfolio_daily_snapshots (account_id);

-- index: ix_portfolio_daily_snapshots_created_at
CREATE INDEX ix_portfolio_daily_snapshots_created_at ON portfolio_daily_snapshots (created_at);

-- index: ix_portfolio_daily_snapshots_snapshot_date
CREATE INDEX ix_portfolio_daily_snapshots_snapshot_date ON portfolio_daily_snapshots (snapshot_date);

-- index: ix_portfolio_fx_rates_from_currency
CREATE INDEX ix_portfolio_fx_rates_from_currency ON portfolio_fx_rates (from_currency);

-- index: ix_portfolio_fx_rates_rate_date
CREATE INDEX ix_portfolio_fx_rates_rate_date ON portfolio_fx_rates (rate_date);

-- index: ix_portfolio_fx_rates_to_currency
CREATE INDEX ix_portfolio_fx_rates_to_currency ON portfolio_fx_rates (to_currency);

-- index: ix_portfolio_lot_account_symbol
CREATE INDEX ix_portfolio_lot_account_symbol ON portfolio_position_lots (account_id, symbol);

-- index: ix_portfolio_position_lots_account_id
CREATE INDEX ix_portfolio_position_lots_account_id ON portfolio_position_lots (account_id);

-- index: ix_portfolio_position_lots_open_date
CREATE INDEX ix_portfolio_position_lots_open_date ON portfolio_position_lots (open_date);

-- index: ix_portfolio_position_lots_symbol
CREATE INDEX ix_portfolio_position_lots_symbol ON portfolio_position_lots (symbol);

-- index: ix_portfolio_position_lots_updated_at
CREATE INDEX ix_portfolio_position_lots_updated_at ON portfolio_position_lots (updated_at);

-- index: ix_portfolio_positions_account_id
CREATE INDEX ix_portfolio_positions_account_id ON portfolio_positions (account_id);

-- index: ix_portfolio_positions_symbol
CREATE INDEX ix_portfolio_positions_symbol ON portfolio_positions (symbol);

-- index: ix_portfolio_positions_updated_at
CREATE INDEX ix_portfolio_positions_updated_at ON portfolio_positions (updated_at);

-- index: ix_portfolio_trade_account_date
CREATE INDEX ix_portfolio_trade_account_date ON portfolio_trades (account_id, trade_date);

-- index: ix_portfolio_trades_account_id
CREATE INDEX ix_portfolio_trades_account_id ON portfolio_trades (account_id);

-- index: ix_portfolio_trades_created_at
CREATE INDEX ix_portfolio_trades_created_at ON portfolio_trades (created_at);

-- index: ix_portfolio_trades_dedup_hash
CREATE INDEX ix_portfolio_trades_dedup_hash ON portfolio_trades (dedup_hash);

-- index: ix_portfolio_trades_symbol
CREATE INDEX ix_portfolio_trades_symbol ON portfolio_trades (symbol);

-- index: ix_portfolio_trades_trade_date
CREATE INDEX ix_portfolio_trades_trade_date ON portfolio_trades (trade_date);

-- index: ix_schema_migrations_applied_at
CREATE INDEX ix_schema_migrations_applied_at ON schema_migrations (applied_at);

-- index: ix_stock_daily_code
CREATE INDEX ix_stock_daily_code ON stock_daily (code);

-- index: ix_stock_daily_date
CREATE INDEX ix_stock_daily_date ON stock_daily (date);
