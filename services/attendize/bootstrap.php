<?php

/**
 * Create the initial Attendize admin account (non-interactive).
 * Mirrors UserSignupController::postSignup without HTTP.
 */

require __DIR__ . '/vendor/autoload.php';
$app = require_once __DIR__ . '/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

use App\Models\Account;
use App\Models\AccountPaymentGateway;
use App\Models\PaymentGateway;
use App\Models\User;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

$email = getenv('ADMIN_EMAIL') ?: 'admin@example.com';
$password = getenv('ADMIN_PASSWORD') ?: 'changeme';

if (User::where('email', $email)->exists()) {
    echo "Admin user already exists: {$email}\n";
    exit(0);
}

$account = Account::create([
    'email' => $email,
    'first_name' => 'Admin',
    'last_name' => 'User',
    'currency_id' => config('attendize.default_currency'),
    'timezone_id' => config('attendize.default_timezone'),
    'is_active' => true,
]);

$user = User::create([
    'email' => $email,
    'first_name' => 'Admin',
    'last_name' => 'User',
    'password' => Hash::make($password),
    'account_id' => $account->id,
    'is_parent' => 1,
    'is_registered' => 1,
    'is_confirmed' => 1,
    'confirmation_code' => Str::random(20),
]);

AccountPaymentGateway::create([
    'payment_gateway_id' => PaymentGateway::getDefaultPaymentGatewayId(),
    'account_id' => $account->id,
    'config' => '{"apiKey":"","publishableKey":""}',
]);

echo "Created admin user: {$email}\n";
