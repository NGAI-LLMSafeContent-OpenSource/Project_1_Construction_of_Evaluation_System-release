import unittest

from runtime_config import (
    get_app_port,
    get_cors_allow_origins,
    get_docs_url,
    get_runtime_mode,
)


class RuntimeConfigTests(unittest.TestCase):
    def test_defaults_to_standalone_mode(self):
        self.assertEqual(get_runtime_mode({}), 'standalone')

    def test_uses_standalone_default_port_without_mode_or_app_port(self):
        self.assertEqual(get_app_port({}), 8000)

    def test_uses_integration_default_port_in_integration_mode(self):
        self.assertEqual(get_app_port({'APP_RUNTIME_MODE': 'integration'}), 6102)

    def test_prefers_explicit_app_port_over_mode_default(self):
        self.assertEqual(
            get_app_port({
                'APP_RUNTIME_MODE': 'integration',
                'APP_PORT': '7001',
            }),
            7001,
        )

    def test_rejects_invalid_app_port_with_clear_error(self):
        with self.assertRaisesRegex(ValueError, 'APP_PORT must be an integer'):
            get_app_port({'APP_PORT': 'not-a-port'})

    def test_uses_default_cors_origins_in_standalone_mode(self):
        self.assertIn('http://127.0.0.1:3000', get_cors_allow_origins({}))
        self.assertIn('http://10.70.200.48:3000', get_cors_allow_origins({}))

    def test_uses_default_cors_origins_in_integration_mode(self):
        origins = get_cors_allow_origins({'APP_RUNTIME_MODE': 'integration'})
        self.assertIn('http://127.0.0.1:6101', origins)
        self.assertIn('http://127.0.0.1:16101', origins)

    def test_parses_explicit_cors_origins(self):
        self.assertEqual(
            get_cors_allow_origins({
                'CORS_ALLOW_ORIGINS': 'http://127.0.0.1:6101, http://127.0.0.1:16101',
            }),
            ['http://127.0.0.1:6101', 'http://127.0.0.1:16101'],
        )

    def test_builds_docs_url_from_host_and_resolved_port(self):
        self.assertEqual(
            get_docs_url({
                'APP_HOST': '0.0.0.0',
                'APP_RUNTIME_MODE': 'integration',
            }),
            'http://localhost:6102/docs',
        )


if __name__ == '__main__':
    unittest.main()
