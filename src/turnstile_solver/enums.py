# -*- mode: python ; coding: utf-8 -*-
from enum import Enum


class CaptchaApiMessageEvent(Enum):
  INIT = "init"
  TRANSLATION_INIT = "translationInit"
  LANGUAGE_UNSUPPORTED = "languageUnsupported"
  REJECT = "reject"
  FOOD = "food"
  OVERRUN_BEGIN = "overrunBegin"
  OVERRUN_END = "overrunEnd"
  COMPLETE = "complete"
  FAIL = "fail"
  FEEDBACK_INIT = "feedbackInit"
  REQUEST_FEEDBACK_DATA = "requestFeedbackData"
  TURNSTILE_RESULTS = "turnstileResults"
  CLOSE_FEEDBACK_REPORT_IFRAME = "closeFeedbackReportIframe"
  TOKEN_EXPIRED = "tokenExpired"
  INTERACTIVE_TIMEOUT = "interactiveTimeout"
  REFRESH_REQUEST = "refreshRequest"
  RELOAD_REQUEST = "reloadRequest"
  INTERACTIVE_BEGIN = "interactiveBegin"
  INTERACTIVE_END = "interactiveEnd"
  WIDGET_STALE = "widgetStale"
  REQUEST_EXTRA_PARAMS = "requestExtraParams"
