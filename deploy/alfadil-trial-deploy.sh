#!/usr/bin/env bash
# ============================================================================
#  منصة الفاضل — نشر تجريبي مجاني (Oracle جدة) ببيانات مصطنعة
#  سكربت موجَّه: يبني الصورة، يشغّل الإنتاج بـHTTPS، ينشئ الموقع، يزرع بيانات
#  مصطنعة، ويتأكّد أن بوابة الإنتاج "مغلقة". يُنفَّذ على الخادم (Ubuntu 22.04).
#
#  ⚠️ لم يُشغَّل هذا السكربت على خادم Oracle حيّ من قِبَلنا — رُوجِع نحوياً فقط.
#     نفّذه خطوة بخطوة وراقب المخرجات. الأسرار تُطلب وقت التشغيل ولا تُخزَّن في Git.
#
#  الحالة الإلزامية: production_privacy_gate = مغلقة، بيانات مصطنعة فقط.
#  التشغيل الفعلي ببيانات حقيقية يتطلّب DPA + DPIA + فتح البوابة يدوياً (راجع docs/15).
# ============================================================================
set -euo pipefail

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mخطأ: %s\033[0m\n' "$*" >&2; exit 1; }

# ---- 0) تحقّق المتطلبات ----
command -v docker >/dev/null 2>&1 || die "Docker غير مثبّت. ثبّته أولاً: curl -fsSL https://get.docker.com | sudo sh"
docker compose version >/dev/null 2>&1 || die "Docker Compose plugin غير متوفّر."

FD_DIR="${FD_DIR:-$HOME/frappe_docker}"
IMAGE="alfadil/trial"
TAG="latest"
REPO="github.com/mdharbi777/stochops-nonprofit-suite"

# ---- 1) المدخلات (الأسرار تُقرأ بلا إظهار) ----
DEFAULT_IP="$(curl -fsS https://api.ipify.org 2>/dev/null || true)"
read -rp "عنوان IP العام للخادم [${DEFAULT_IP:-أدخله}]: " SERVER_IP
SERVER_IP="${SERVER_IP:-$DEFAULT_IP}"
[ -n "$SERVER_IP" ] || die "لا بدّ من عنوان IP."
SITE="${SERVER_IP}.sslip.io"

read -rsp "GitHub Personal Access Token (قراءة المستودع الخاص): " GH_TOKEN; echo
[ -n "$GH_TOKEN" ] || die "التوكن مطلوب لبناء المستودع الخاص."
read -rsp "كلمة مرور قاعدة البيانات (جديدة، قوية): " DB_PASSWORD; echo
[ -n "$DB_PASSWORD" ] || die "كلمة مرور قاعدة البيانات مطلوبة."
read -rsp "كلمة مرور مدير الموقع (Administrator، قوية): " ADMIN_PASSWORD; echo
[ -n "$ADMIN_PASSWORD" ] || die "كلمة مرور المدير مطلوبة."

say "الموقع سيكون: https://${SITE}/nos"

# ---- 2) تجهيز frappe_docker ----
if [ ! -d "$FD_DIR" ]; then
  say "استنساخ frappe_docker"
  git clone https://github.com/frappe/frappe_docker "$FD_DIR"
fi
cd "$FD_DIR"

# ---- 3) بناء الصورة المخصّصة (التوكن يُحقن وقت البناء فقط ثم يُمحى) ----
say "بناء الصورة (Frappe v15 + منصة الفاضل) — قد يستغرق 15–30 دقيقة على ARM"
TMP_APPS="$(mktemp)"
cat > "$TMP_APPS" <<EOF
[
  { "url": "https://github.com/frappe/frappe", "branch": "version-15" },
  { "url": "https://${GH_TOKEN}@${REPO}", "branch": "main" }
]
EOF
APPS_JSON_BASE64="$(base64 -w 0 "$TMP_APPS")"
shred -u "$TMP_APPS" 2>/dev/null || rm -f "$TMP_APPS"   # امحُ الملف الحاوي للتوكن فوراً

docker build \
  --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg=FRAPPE_BRANCH=version-15 \
  --build-arg=APPS_JSON_BASE64="$APPS_JSON_BASE64" \
  --tag="${IMAGE}:${TAG}" \
  --file=images/layered/Containerfile .
unset GH_TOKEN APPS_JSON_BASE64   # لا تُبقِ التوكن في الذاكرة البيئية

# ---- 4) ملف البيئة ----
say "كتابة .env"
cat > .env <<EOF
CUSTOM_IMAGE=${IMAGE}
CUSTOM_TAG=${TAG}
PULL_POLICY=never
SITES=\`${SITE}\`
DB_PASSWORD=${DB_PASSWORD}
LETSENCRYPT_EMAIL=ops@stochops.com
EOF

# ---- 5) تشغيل الإنتاج مع HTTPS ----
say "تشغيل الحاويات (MariaDB + Redis + HTTPS)"
docker compose \
  -f compose.yaml \
  -f overrides/compose.mariadb.yaml \
  -f overrides/compose.redis.yaml \
  -f overrides/compose.https.yaml \
  --env-file .env up -d

say "انتظار جاهزية الخدمة الخلفية (قد تصل دقيقة)"
for i in $(seq 1 30); do
  if docker compose exec -T backend bench version >/dev/null 2>&1; then break; fi
  sleep 5
done

# ---- 6) إنشاء الموقع + تثبيت التطبيق ----
say "إنشاء الموقع ${SITE} وتثبيت منصة الفاضل"
docker compose exec -T backend bench new-site "$SITE" \
  --db-root-password "$DB_PASSWORD" \
  --admin-password "$ADMIN_PASSWORD" \
  --install-app stochops_nonprofit
unset DB_PASSWORD ADMIN_PASSWORD

docker compose exec -T backend bench --site "$SITE" scheduler enable

# ---- 7) تحقّق التثبيت + بيانات مصطنعة ----
say "التحقّق من التثبيت (المتوقّع all_ok: true)"
docker compose exec -T backend bench --site "$SITE" execute stochops_nonprofit.setup.verify_install.run

say "زرع بيانات مصطنعة (للعرض فقط)"
docker compose exec -T backend bench --site "$SITE" execute stochops_nonprofit.setup.seed_demo.run

# ---- 8) تأكيد أن بوابة الإنتاج مغلقة (إلزامي) ----
say "التأكد من أن production_privacy_gate مغلقة"
GATE="$(docker compose exec -T backend bench --site "$SITE" execute \
  frappe.db.get_single_value --args "['Privacy Configuration','production_privacy_gate']" 2>/dev/null | tr -d '[:space:]')"
case "$GATE" in
  0|None|"") printf '\n\033[1;32mالبوابة مغلقة (%s) — بيئة تجريبية آمنة.\033[0m\n' "${GATE:-None}" ;;
  *) die "تحذير: بوابة الإنتاج ليست مغلقة (القيمة=${GATE}). أوقف الاستخدام وراجع الإعداد فوراً." ;;
esac

say "تمّ. افتح: https://${SITE}/nos"
cat <<'NOTE'

الخطوات التالية (يدوية):
  • لاختبار البريد: اضبط إعداد Resend (587/STARTTLS) كما في deploy/.env.example، ثم جرّب رسالة.
  • أنشئ حساب مدير الجمعية عبر الدعوة: /nos/accounts (داخل المنصة).
  • بيان صريح للجمعية: نسخة تجريبية ببيانات مصطنعة، بلا بيانات حقيقية، قد تُعاد تهيئتها.
  • التشغيل الفعلي ببيانات حقيقية ممنوع حتى: DPA موقّع + DPIA معتمد + استضافة سعودية + فتح البوابة يدوياً (docs/15 §10).
NOTE
