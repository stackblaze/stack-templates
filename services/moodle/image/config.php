<?php
// StackBlaze: Moodle configuration from the environment (see config-dist.php
// for every option). Values set here override the admin UI and show as locked
// there. Rebuild the image to change them, or set the variables named below.

unset($CFG);
global $CFG;
$CFG = new stdClass();

$CFG->dbtype    = 'pgsql';
$CFG->dblibrary = 'native';
$CFG->dbhost    = getenv('MOODLE_DB_HOST');
$CFG->dbname    = getenv('MOODLE_DB_NAME');
$CFG->dbuser    = getenv('MOODLE_DB_USER');
$CFG->dbpass    = getenv('MOODLE_DB_PASSWORD');
$CFG->prefix    = 'mdl_';
$CFG->dboptions = [
    'dbpersist' => false,
    'dbsocket'  => false,
    'dbport'    => (int) (getenv('MOODLE_DB_PORT') ?: 5432),
];

// The site address (MOODLE_URL, the app URL by default). Moodle redirects every
// other host name here, so change MOODLE_URL when you add a custom domain.
$CFG->wwwroot  = rtrim((string) getenv('MOODLE_URL'), '/');
$CFG->dataroot = '/var/www/moodledata';
$CFG->admin    = 'admin';
$CFG->directorypermissions = 02777;

// TLS ends at the platform's edge.
$CFG->sslproxy = true;
// Apache sends unknown paths to r.php (apache.conf FallbackResource).
$CFG->routerconfigured = true;

// moodledata is a shared network volume: keep the per-node cache on local
// disk, and sessions in the database (no file locks on the volume).
$CFG->localcachedir = '/var/cache/moodle';
$CFG->session_handler_class = '\core\session\database';
$CFG->session_database_acquire_lock_timeout = 120;

// Code execution from the web UI is off:
// - no plugin installs or updates from Site administration (the code in the
//   image is read-only anyway; add plugins by building a new image);
// - executable paths cannot be changed from the web.
$CFG->disableupdateautodeploy = true;
$CFG->preventexecpath = true;
$CFG->pathtogs  = '/usr/bin/gs';
$CFG->pathtophp = '/usr/local/bin/php';
$CFG->pathtodu  = '/usr/bin/du';
$CFG->aspellpath = '';
$CFG->pathtodot  = '';

// Cron runs in the worker (admin/cli/cron.php every minute), never from the web.
$CFG->cronclionly = true;

// Email through the platform Email add-on (SMTP_* are injected while it is
// connected). SMTP_FROM is "address" or "Name <address>"; the relay accepts
// only that sender, so every message goes out from it (Reply-To keeps the
// real author).
if (getenv('SMTP_HOST')) {
    $port = (int) (getenv('SMTP_PORT') ?: 587);
    $CFG->smtphosts = getenv('SMTP_HOST') . ':' . $port;
    $CFG->smtpsecure = $port === 465 ? 'ssl' : 'tls';
    $CFG->smtpauthtype = 'LOGIN';
    $CFG->smtpuser = (string) getenv('SMTP_USER');
    $CFG->smtppass = (string) getenv('SMTP_PASSWORD');
    $from = trim((string) getenv('SMTP_FROM'));
    if (preg_match('/<([^>]+)>/', $from, $m)) {
        $from = trim($m[1]);
    }
    if ($from !== '') {
        $CFG->noreplyaddress = $from;
    }
    // Empty = never send from a user's own address (can_send_from_real_email_address).
    $CFG->allowedemaildomains = '';
}

require_once(__DIR__ . '/lib/setup.php');
// There is no php closing tag in this file, it is intentional because it
// prevents trailing whitespace problems!
