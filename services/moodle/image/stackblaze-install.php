<?php
// StackBlaze: installs or upgrades Moodle from the command line before Apache
// starts, so Moodle's web installer (and its "set up the admin account" page)
// is never open to the first visitor.
//
//   php install.php wait     wait for a real database login
//   php install.php install  install (first start) or upgrade, then verify
//   php install.php ready    exit 0 once the install is complete (worker)
//
// Runs as www-data. Prints no secrets.

$mode = $argv[1] ?? 'install';
$dir = '/var/www/moodle';

function say($msg) {
    fwrite(STDOUT, "[stackblaze] $msg\n");
}

function connect($quiet = false) {
    $conn = sprintf("host=%s port=%d dbname=%s user=%s password=%s connect_timeout=5",
        getenv('MOODLE_DB_HOST'), (int) (getenv('MOODLE_DB_PORT') ?: 5432),
        getenv('MOODLE_DB_NAME'), getenv('MOODLE_DB_USER'), getenv('MOODLE_DB_PASSWORD'));
    $db = @pg_connect($conn, PGSQL_CONNECT_FORCE_NEW);
    if (!$db && !$quiet) {
        say('database not reachable yet');
    }
    return $db;
}

function value($db, $sql, $params = []) {
    $r = @pg_query_params($db, $sql, $params);
    if (!$r) {
        return null;
    }
    $row = pg_fetch_row($r);
    return $row ? $row[0] : null;
}

// 'none' (no tables), 'partial' (an install that never finished) or 'complete'.
function state($db) {
    if (value($db, "SELECT to_regclass('public.mdl_config')") === null) {
        return 'none';
    }
    // install_cli_database() sets rolesactive after the admin password.
    return value($db, "SELECT value FROM mdl_config WHERE name = 'rolesactive'") === '1' ? 'complete' : 'partial';
}

function run($cmd) {
    passthru($cmd, $code);
    return $code;
}

function need($name) {
    $v = (string) getenv($name);
    if ($v === '') {
        say("$name is not set");
        exit(1);
    }
    return $v;
}

if ($mode === 'wait') {
    for ($i = 0; $i < 300; $i++) {
        if (($db = connect($i % 10 !== 0)) && value($db, 'SELECT 1') === '1') {
            exit(0);
        }
        sleep(2);
    }
    say('gave up waiting for the database');
    exit(1);
}

if ($mode === 'ready') {
    $db = connect(true);
    exit($db && state($db) === 'complete' ? 0 : 1);
}

$url = need('MOODLE_URL');
if (!parse_url($url, PHP_URL_HOST)) {
    say('MOODLE_URL has no host');
    exit(1);
}

$db = connect();
if (!$db) {
    exit(1);
}
// One installer at a time (several web pods start together).
value($db, 'SELECT pg_advisory_lock(803530)');

$state = state($db);
if ($state === 'partial') {
    // Nobody can have used a site whose install never finished: start over.
    say('an earlier install did not finish; removing its tables and installing again');
    $r = pg_query($db, "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'mdl\\_%'");
    while ($row = pg_fetch_row($r)) {
        pg_query($db, 'DROP TABLE IF EXISTS "' . str_replace('"', '', $row[0]) . '" CASCADE');
    }
    $state = 'none';
}

if ($state === 'none') {
    say('installing Moodle (first start, takes a few minutes)');
    $pass = need('MOODLE_ADMIN_PASSWORD');
    $cmd = 'php ' . escapeshellarg("$dir/admin/cli/install_database.php")
        . ' --agree-license --lang=en'
        . ' --adminuser=' . escapeshellarg(getenv('MOODLE_ADMIN_USER') ?: 'admin')
        . ' --adminpass=' . escapeshellarg($pass)
        . ' --adminemail=' . escapeshellarg(getenv('MOODLE_ADMIN_EMAIL') ?: 'admin@example.com')
        . ' --fullname=' . escapeshellarg(getenv('MOODLE_SITE_NAME') ?: 'Moodle')
        . ' --shortname=' . escapeshellarg(getenv('MOODLE_SITE_SHORTNAME') ?: 'moodle')
        . ' > /tmp/moodle-install.log 2>&1';
    $code = run($cmd);
    if ($code !== 0) {
        say("install failed (exit $code); last lines:");
        run('tail -n 30 /tmp/moodle-install.log');
        exit(1);
    }
    // Check the result, not just the exit code.
    $user = getenv('MOODLE_ADMIN_USER') ?: 'admin';
    $hash = value($db, "SELECT password FROM mdl_user WHERE username = $1 AND deleted = 0", [$user]);
    if (state($db) !== 'complete' || !$hash || !password_verify($pass, $hash)) {
        say('install finished but the site or the admin login is missing');
        exit(1);
    }
    // Let people pick light or dark mode (Boost colour modes, off upstream).
    // A first-install default only: admins can switch it off again.
    run('php ' . escapeshellarg("$dir/admin/cli/cfg.php") . ' --component=theme_boost --name=enablecolourmodes --set=1 > /dev/null');
    say("Moodle installed; sign in as '$user' with MOODLE_ADMIN_PASSWORD");
} else {
    // A newer image: run the upgrade before serving pages.
    $code = run('php ' . escapeshellarg("$dir/admin/cli/upgrade.php") . ' --is-pending > /dev/null 2>&1');
    if ($code === 2) {
        say('upgrading Moodle to the version in this image');
        if (run('php ' . escapeshellarg("$dir/admin/cli/upgrade.php") . ' --non-interactive') !== 0) {
            say('upgrade failed');
            exit(1);
        }
    } else if ($code !== 0) {
        say("upgrade check failed (exit $code)");
        exit(1);
    }
    say('Moodle is installed and up to date');
}
value($db, 'SELECT pg_advisory_unlock(803530)');
exit(0);
