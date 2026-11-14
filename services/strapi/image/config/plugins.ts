import type { Core } from '@strapi/strapi';

const allowedMediaTypes = [
  'image/*',
  'video/*',
  'audio/*',
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.*',
  'text/plain',
  'text/csv',
];

const deniedTypes = [
  'image/svg+xml',
  'application/vnd.microsoft.portable-executable',
  'application/x-msdownload',
  'application/x-msdos-program',
  'application/x-executable',
  'application/x-dosexec',
  'application/x-sh',
  'text/x-shellscript',
  'application/x-mach-binary',
];

const config = ({ env }: Core.Config.Shared.ConfigParams): Core.Config.Plugin => {
  const plugins: Core.Config.Plugin = {
    'users-permissions': {
      config: {
        jwtManagement: 'refresh',
        sessions: {
          httpOnly: true,
        },
      },
    },
    upload: {
      config: {
        security: {
          allowedTypes: allowedMediaTypes,
          deniedTypes,
        },
      },
    },
  };

  // Email goes out over SMTP. The StackBlaze Email add-on injects SMTP_HOST,
  // SMTP_PORT, SMTP_USER, SMTP_PASSWORD and SMTP_FROM. Strapi's default
  // provider (sendmail) delivers straight to the recipient's MX on port 25,
  // which cloud networks block, so without SMTP_HOST mail sends fail.
  if (env('SMTP_HOST')) {
    const port = env.int('SMTP_PORT', 587);
    plugins.email = {
      config: {
        provider: 'nodemailer',
        providerOptions: {
          host: env('SMTP_HOST'),
          port,
          secure: port === 465,
          auth: {
            user: env('SMTP_USER'),
            pass: env('SMTP_PASSWORD'),
          },
        },
        settings: {
          defaultFrom: env('SMTP_FROM'),
          defaultReplyTo: env('SMTP_REPLY_TO', env('SMTP_FROM')),
        },
      },
    };
  }

  return plugins;
};

export default config;
