<?php
$CONFIG = array (
  'trusted_domains' => 
  array (
    {% for h in nextcloud_trusted_domains %}
    {{loop.index0}} => '{{h}}',
    {% endfor %}
  ),
  {% if nextcloud_trusted_proxies|length > 0 %}
  'trusted_proxies' => 
  array (
    {% for p in nextcloud_trusted_proxies %}
    {{loop.index0}} => '{{p}}',
    {% endfor %}
  ),
  'forwarded_for_headers' => 
  array (
    {% for h in nextcloud_forwarded_for_headers %}
    {{loop.index0}} => '{{h}}',
    {% endfor %}
  ),
  {% endif %}
  'overwritehost' => '{{nextcloud_trusted_domains|first}}',
  'overwritewebroot' => '{{nextcloud_web_root}}',
  'memcache.local' => '\\OC\\Memcache\\APCu',
  'filelocking.enabled' => true,
  'memcache.locking' => '\\OC\\Memcache\\Redis',
  'redis' => 
  array (
    'host' => '/var/run/redis/redis-server.sock',
    'port' => 0,
    'dbindex' => 0,
    'timeout' => 10.0,
    'read_timeout' => 10.0,
  ),
  'log_type' => 'file',
  'log_type_audit' => 'file',
  'logfilemode' => 0640,
  'logfile' =>       '/var/log/nextcloud_{{nextcloud_www_dir}}/nextcloud.log',
  'logfile_audit' => '/var/log/nextcloud_{{nextcloud_www_dir}}/audit.log',
  'updater.release.channel' => 'stable',
  'upgrade.disable-web' => true,
  {% if nextcloud_mail_from_address is defined %}
  'mail_smtpmode' => 'smtp',
  'mail_smtpport' => '25',
  'mail_domain' => '{{nextcloud_mail_domain}}',
  'mail_from_address' => '{{nextcloud_mail_from_address}}',
  'mail_smtphost' => '{{nextcloud_mail_smtphost}}',
  {% endif %}
  'default_phone_region' => '{{nextcloud_default_phone_region}}',
);
