import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import time

# ضع توكن البوت هنا
TOKEN = "MTQ3MjY1NzcwMDE2MzgxNzQ4Mg.GE6Xjc.TWLhIUVBiMQSOjwjFFQU40xDFxlWaPQxxWyemg"

# =========================
# إعدادات البوت
# =========================

CURRENCY = "<:emoji_1:1473735074053619722>"  # ضع هنا ايموجي العملة الخاص بك

DAILY_REWARD = 500
WORK_MIN = 50
WORK_MAX = 200

DAILY_COOLDOWN = 86400  # 24 ساعة
WORK_COOLDOWN = 60       # 1 دقيقة

SHOP_ITEMS = {
    "pizza": {"price": 100},
    "pc": {"price": 1200},
    "car": {"price": 5000}
}

DATA_FILE = "economy.json"

# =========================

intents = discord.Intents.default()
intents.message_content = True  # مهم جدا للأوامر
bot = commands.Bot(command_prefix="!", intents=intents)

tree = bot.tree  # لتسهيل استخدام slash commands


# =========================
# دوال التعامل مع البيانات
# =========================
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def ensure_user(data, user_id):
    if str(user_id) not in data:
        data[str(user_id)] = {
            "wallet": 0,
            "bank": 0,
            "inventory": {},
            "last_daily": 0,
            "last_work": 0,
            "used_codes": []
        }


# =========================
# حدث تشغيل البوت
# =========================
@bot.event
async def on_ready():
    await tree.sync()
    print("Bot is ready")


# =========================
# /balance
# =========================
@tree.command(name="balance")
async def balance(interaction: discord.Interaction):
    data = load_data()
    ensure_user(data, interaction.user.id)

    user = data[str(interaction.user.id)]
    embed = discord.Embed(title="Balance")
    embed.add_field(name="Wallet", value=f"{user['wallet']} {CURRENCY}")
    embed.add_field(name="Bank", value=f"{user['bank']} {CURRENCY}")

    await interaction.response.send_message(embed=embed)


# =========================
# /daily
# =========================
@tree.command(name="daily")
async def daily(interaction: discord.Interaction):
    data = load_data()
    ensure_user(data, interaction.user.id)

    user = data[str(interaction.user.id)]
    now = time.time()

    if now - user["last_daily"] < DAILY_COOLDOWN:
        remaining = int(DAILY_COOLDOWN - (now - user["last_daily"]))
        await interaction.response.send_message(f"⏳ Cooldown: {remaining} ثواني")
        return

    user["wallet"] += DAILY_REWARD
    user["last_daily"] = now
    save_data(data)

    await interaction.response.send_message(f"🎉 You got {DAILY_REWARD} {CURRENCY}")


# =========================
# /work
# =========================
@tree.command(name="work")
async def work(interaction: discord.Interaction):
    data = load_data()
    ensure_user(data, interaction.user.id)

    user = data[str(interaction.user.id)]
    now = time.time()

    if now - user["last_work"] < WORK_COOLDOWN:
        remaining = int(WORK_COOLDOWN - (now - user["last_work"]))
        await interaction.response.send_message(f"⏳ Cooldown: {remaining} ثواني")
        return

    earnings = random.randint(WORK_MIN, WORK_MAX)
    user["wallet"] += earnings
    user["last_work"] = now
    save_data(data)

    await interaction.response.send_message(f"💼 You earned {earnings} {CURRENCY}")


# =========================
# /shop
# =========================
@tree.command(name="shop")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="Shop")
    for item, info in SHOP_ITEMS.items():
        embed.add_field(name=item, value=f"{info['price']} {CURRENCY}")
    await interaction.response.send_message(embed=embed)


# =========================
# /buy
# =========================
@tree.command(name="buy")
@app_commands.describe(item="اسم العنصر الذي تريد شراؤه")
async def buy(interaction: discord.Interaction, item: str):
    data = load_data()
    ensure_user(data, interaction.user.id)

    item = item.lower()
    if item not in SHOP_ITEMS:
        await interaction.response.send_message("❌ Item not found")
        return

    price = SHOP_ITEMS[item]["price"]
    user = data[str(interaction.user.id)]

    if user["wallet"] < price:
        await interaction.response.send_message("❌ Not enough money")
        return

    user["wallet"] -= price
    user["inventory"][item] = user["inventory"].get(item, 0) + 1
    save_data(data)

    await interaction.response.send_message(f"✅ You bought {item}")


# =========================
# /inventory
# =========================
@tree.command(name="inventory")
async def inventory(interaction: discord.Interaction):
    data = load_data()
    ensure_user(data, interaction.user.id)

    inv = data[str(interaction.user.id)]["inventory"]
    if not inv:
        await interaction.response.send_message("📦 Inventory empty")
        return

    embed = discord.Embed(title="Inventory")
    for item, amount in inv.items():
        embed.add_field(name=item, value=f"x{amount}")

    await interaction.response.send_message(embed=embed)


# =========================
# /createcode (admin فقط)
# =========================
@tree.command(name="createcode")
@app_commands.describe(code="اسم الكود", amount="قيمة المكافأة", uses="عدد الاستخدامات")
async def createcode(interaction: discord.Interaction, code: str, amount: int, uses: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only", ephemeral=True)
        return

    data = load_data()
    if "codes" not in data:
        data["codes"] = {}

    data["codes"][code] = {"amount": amount, "uses": uses}
    save_data(data)
    await interaction.response.send_message(f"✅ Code `{code}` created: {amount} {CURRENCY}, Uses: {uses}")


# =========================
# /redeem
# =========================
@tree.command(name="redeem")
@app_commands.describe(code="ادخل الكود")
async def redeem(interaction: discord.Interaction, code: str):
    data = load_data()
    ensure_user(data, interaction.user.id)

    if "codes" not in data or code not in data["codes"]:
        await interaction.response.send_message("❌ Invalid code")
        return

    code_data = data["codes"][code]
    if code_data["uses"] <= 0:
        await interaction.response.send_message("❌ Code expired")
        return

    user = data[str(interaction.user.id)]
    if code in user["used_codes"]:
        await interaction.response.send_message("❌ You already used this code")
        return

    user["wallet"] += code_data["amount"]
    user["used_codes"].append(code)
    code_data["uses"] -= 1
    save_data(data)

    await interaction.response.send_message(f"🎉 You got {code_data['amount']} {CURRENCY}")


# =========================
# تشغيل البوت
# =========================
bot.run(TOKEN)
