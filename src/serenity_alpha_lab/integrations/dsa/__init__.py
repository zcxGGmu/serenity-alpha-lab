"""Compatibility entry points for the isolated DSA upstream worktree."""

from serenity_alpha_lab.integrations.dsa.task_backend import DsaAnalysisTaskQueueBackend

__all__ = ["DsaAnalysisTaskQueueBackend"]
