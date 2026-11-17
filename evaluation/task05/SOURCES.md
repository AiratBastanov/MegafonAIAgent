# Использованные первичные руководства

Прочитаны через web 16.11.2026, только для реальных вопросов протокола/host. Это не предметные источники продукта и не новые snapshots Dropbox.

- [Subagents, ChatGPT Learn](https://learn.chatgpt.com/docs/agent-configuration/subagents), раздел Approvals and sandbox controls / Custom agents: контекст и права не изолируются простой ролевой инструкцией; skills/permissions могут наследоваться. Точный доступ этого host проверен capability probe и установленным CLI help, а не перенесён из current-main flags.
- [Evaluation best practices, OpenAI](https://developers.openai.com/api/docs/guides/evaluation-best-practices), раздел model graders: порядок и длина ответов могут влиять на оценку. Применены явная короткая rubric, псевдонимы и порядок, заданный до review; human calibration отсутствует.
- [Demystifying evals for AI agents, Anthropic](https://www.anthropic.com/research/demystifying-evals-for-ai-agents), Structure / Evaluating agents: ответы и фактическое конечное состояние оцениваются отдельно, вместе с trace. Здесь сохранение проверяется по файлам/loader, а не только по заявлению участника.

Codex Prompting Guide.txt; Model guidance _ OpenAI API.txt; Rethinking skills and prompts for GPT-6 Astra _ OpenAI Developers.txt; PromptGuide.txt; AgentsMD.txt; PersonalizeChatGpt.txt в доступном списке workspace не найдены, прочитанными не заявляются. Чужие каталоги ради дубликатов не исследовались. Применены явно заданные пользователем outcome-first execution, progressive loading, полезная делегация и соразмерные проверки.
