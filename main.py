import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import os

# Налаштовуємо інтенції бота та створюємо екземпляр бота
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Словник для зберігання тікетів
tickets = {}
ticket_counter = 1

# ID каналу для надсилання повідомлень
CHANNEL_ID = 1250019961905217686
LOG_CHANNEL_ID = 1254109085352333332

# ID ролей підтримки
SUPPORT_ROLE_IDS = [1199839255220994078, 1248205289799290961, 1199845158460592219, 1199845190349897788]

# Подія, яка виконується, коли бот готовий
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    try:
        print(f"Attempting to get channel with ID {CHANNEL_ID}")
        channel = bot.get_channel(CHANNEL_ID)
        
        if channel is None:
            print(f"Channel with ID {CHANNEL_ID} not found.")
        else:
            print(f"Channel with ID {CHANNEL_ID} found: {channel}")
            await channel.send(
                embed=discord.Embed(title="Підтримка", description="Натисніть кнопку нижче, щоб створити тікет"),
                view=TicketCreateView()
            )
            print(f"Message sent to channel ID {CHANNEL_ID}.")
    except Exception as e:
        print(f"An error occurred while sending message to channel: {e}")
    check_tickets.start()

class TicketCreateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        print("TicketCreateView initialized")

    @discord.ui.button(label="Створити тікет", style=discord.ButtonStyle.green)
    async def create_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        global ticket_counter
        print(f"Button clicked by {interaction.user}. Creating ticket...")
        try:
            print("Attempting to create ticket channel...")
            guild = interaction.guild
            print(f"Guild: {guild}")

            print(f"Bot permissions in the guild: {guild.me.guild_permissions}")

            if not guild.me.guild_permissions.manage_channels:
                print("Bot does not have permission to manage channels")
                await interaction.response.send_message("Бот не має дозволу на керування каналами.", ephemeral=True)
                return

            print(f"Creating channel with name: ticket-{ticket_counter}")
            ticket_channel = await guild.create_text_channel(f"ticket-{ticket_counter}")
            ticket_counter += 1
            print(f"Ticket channel created: {ticket_channel}")

            # Задаємо права доступу до каналу
            await ticket_channel.set_permissions(guild.default_role, read_messages=False)
            for role_id in SUPPORT_ROLE_IDS:
                support_role = guild.get_role(role_id)
                if support_role:
                    print(f"Setting permissions for role: {support_role}")
                    await ticket_channel.set_permissions(support_role, read_messages=True, send_messages=True)
            await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
            print(f"Permissions set for {interaction.user} in channel {ticket_channel}")

            tickets[ticket_channel.id] = {
                "user": interaction.user.id,
                "created_at": datetime.utcnow()
            }
            print(f"Ticket info saved: {tickets[ticket_channel.id]}")

            await ticket_channel.send(
                f"{interaction.user.mention}, ваш тікет створено! Адміністрація скоро зв'яжеться з вами.",
                view=TicketCloseView(ticket_channel.id)
            )
            print(f"Message sent in ticket channel {ticket_channel.id}")

            await interaction.response.send_message("Тікет успішно створено!", ephemeral=True)
            print(f"Ticket channel {ticket_channel.name} created for {interaction.user}.")
        except Exception as e:
            print(f"Error creating ticket channel: {e}")
            await interaction.response.send_message(f"Помилка створення тікету: {e}", ephemeral=True)

class TicketCloseView(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        print(f"TicketCloseView initialized for channel {channel_id}")

    @discord.ui.button(label="Закрити тікет", style=discord.ButtonStyle.red)
    async def close_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        print(f"Closing ticket in channel {self.channel_id}")
        try:
            channel = bot.get_channel(self.channel_id)
            await channel.send("Тікет закрито! Канал буде видалено через 7 днів.")
            print(f"Close message sent in channel {self.channel_id}")

            tickets[self.channel_id]['closed_at'] = datetime.utcnow()
            print(f"Ticket close time updated: {tickets[self.channel_id]['closed_at']}")

            await channel.set_permissions(interaction.guild.default_role, send_messages=False, read_messages=False)
            print(f"Permissions updated for channel {self.channel_id}")

            await interaction.response.send_message("Тікет успішно закрито!", ephemeral=True)
            print(f"Ticket in channel {self.channel_id} closed.")
        except Exception as e:
            print(f"Error closing ticket: {e}")
            await interaction.response.send_message(f"Помилка закриття тікету: {e}", ephemeral=True)

@tasks.loop(minutes=1)
async def check_tickets():
    now = datetime.utcnow()
    to_delete = []
    print(f"Checking tickets at {now}")
    for channel_id, ticket_info in tickets.items():
        if 'closed_at' in ticket_info and now > ticket_info['closed_at'] + timedelta(days=7):
            print(f"Ticket in channel {channel_id} is ready for deletion.")
            try:
                channel = bot.get_channel(channel_id)
                if channel:
                    await channel.delete()
                    print(f"Channel {channel_id} deleted.")
                to_delete.append(channel_id)
            except Exception as e:
                print(f"Error deleting channel {channel_id}: {e}")
    for channel_id in to_delete:
        try:
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            user = bot.get_user(tickets[channel_id]['user'])
            created_at = tickets[channel_id]['created_at']
            closed_at = tickets[channel_id]['closed_at']
            await log_channel.send(
                f"Тікет від {user.mention} створений {created_at} закрито {closed_at} видалено."
            )
            print(f"Log message sent for ticket in channel {channel_id}")

            del tickets[channel_id]
            print(f"Ticket info deleted for channel {channel_id}")
        except Exception as e:
            print(f"Error logging ticket deletion for channel {channel_id}: {e}")

def main():
    print("Starting bot")
    token = os.getenv('BOT_TOKEN')
    if token is None:
        raise ValueError("No BOT_TOKEN provided")
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.start(token))
    except Exception as e:
        print(f"An error occurred while running the bot: {e}")

if __name__ == "__main__":
    main()
