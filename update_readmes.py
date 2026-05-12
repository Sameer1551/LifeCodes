from pathlib import Path

root = Path('d:/zzzLifecodes')
readmes = [
    '01_file_tools/README.md','02_data_tools/README.md','03_scraping_tools/README.md','04_automation/README.md','05_api_tools/README.md',
    '06_ml_tools/README.md','07_security_tools/README.md','08_cli_templates/README.md','09_web_templates/README.md',
    '09_web_templates/fastapi_starter/README.md','09_web_templates/flask_starter/README.md','09_web_templates/react_dashboard/README.md',
    '10_testing_utils/README.md','11_logging_utils/README.md','12_system_utils/README.md','13_visualization_utils/README.md',
    '14_chatbot_utils/README.md','15_dev_productivity_utils/README.md','ectract files to text/README.md'
]

specs = {
    '01_file_tools': 'Provide file read/write operations, path helpers, and file management utilities; howtousefile.md explains usage patterns.',
    '02_data_tools': 'Data import/export, transformation options, and JSON config-driven transformations for ETL workflows; transform_cfg.json defines mapping rules.',
    '03_scraping_tools': 'web_scraper.py collects data from web pages and supports customizable scraping flows; quickcliexample contains CLI usage.',
    '04_automation': 'automation_tools.py defines utility actions for task automation and workflow orchestration.',
    '05_api_tools': 'api_boilerplate.py starts an API server (Flask/FastAPI), defines routes, and example behavior.',
    '06_ml_tools': 'logger_setup.py configures ML-appropriate logging for experiments and model results.',
    '07_security_tools': 'batch_processor.py and progress_runner.py for secure bulk processing; cli_template.py for command-line security utility patterns.',
    '08_cli_templates': 'ml_utils.py demonstrates CLI argument parsing and utility command patterns; quickclidemo.md shows examples.',
    '09_web_templates': 'Container for FastAPI, Flask, and React starters with web app scaffolding.',
    '09_web_templates/fastapi_starter': 'FastAPI app with authentication endpoints, JWT management in jwt_helper.py.',
    '09_web_templates/flask_starter': 'Flask app with auth routes, config, and JWT helpers.',
    '09_web_templates/react_dashboard': 'React app UI structure for dashboard rendering and component-based state.',
    '10_testing_utils': 'api_test_runner.py runs API tests, load_test.py exercises performance tests, unit_test_template.py shows pytest structure.',
    '11_logging_utils': 'system_utils.py supplies logging, diagnostics, and health-check utilities.',
    '12_system_utils': 'security_utils.py includes system and security helper functions.',
    '13_visualization_utils': 'visualization_utils.py provides chart generation and plotting utilities.',
    '14_chatbot_utils': 'Modules implement intent detection, prompt building, memory tracking, and response generation for chatbots.',
    '15_dev_productivity_utils': 'code_stats.py calculates code metrics, doc_generator.py builds docs, formatter.py formats code, project_creator.py scaffolds projects.',
    'ectract files to text': 'extract_texts.py reads files and extracts text content for indexing; filestotext.md explains options.'
}

for rel in readmes:
    path = root / rel
    if not path.exists():
        print('missing', path)
        continue
    text = path.read_text(encoding='utf-8')

    # Remove existing Our sections so we can re-add cleanly
    if '## What these files do' in text:
        pre, rest = text.split('## What these files do', 1)
        if '## How to run' in rest:
            rest = '## How to run' + rest.split('## How to run', 1)[1]
        else:
            rest = ''
        text = pre + rest

    if '## Importance' in text:
        pre, rest = text.split('## Importance', 1)
        # keep any following heading after importance
        if '## ' in rest:
            rest = '## ' + rest.split('## ', 1)[1]
        else:
            rest = ''
        text = pre + rest

    if '## How to run' in text:
        before, after = text.split('## How to run', 1)
    else:
        before, after = text, ''

    section = '\n## What these files do\n'
    key = Path(rel).parent.as_posix()
    section += specs.get(key, 'These files contain tools for this feature folder.') + '\n\n'
    section += 'This section explains specific module responsibilities and their role in the workspace.\n\n'
    section += '## Importance\n'
    if key == '09_web_templates':
        section += 'This subtree provides web app starter templates that help bootstrap frontend and backend projects.\n'
    else:
        section += 'This section is important for building and running project components reliably.\n'

    if '## How to run' in text:
        new_text = before + section + '## How to run' + after
    else:
        new_text = before + section

    path.write_text(new_text, encoding='utf-8')
    print('updated', path)
