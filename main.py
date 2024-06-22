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

# ID каналу для надсилання повідомлень
CHANNEL_ID = 1250019961905217686
LOG_CHANNEL_ID = 1254109085352333332

# Подія, яка виконується, коли бот готовий
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    
    try:
        # Спроба отримати канал за ID
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
        print(f"An error occurred: {e}")
    check_tickets.start()

# Клас для створення тікетів
class TicketCreateView(discord.ui.View):
    @discord.ui.button(label="Створити тікет", style=discord.ButtonStyle.green)
    async def create_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        print(f"Creating ticket for {interaction.user}")
        try:
            ticket_channel = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name}")
            tickets[ticket_channel.id] = {
                "user": interaction.user.id,
                "created_at": datetime.utcnow()
            }
            await ticket_channel.send(
                f"{interaction.user.mention}, ваш тікет створено! Адміністрація скоро зв'яжеться з вами.",
                view=TicketCloseView(ticket_channel.id)
            )
            await interaction.response.send_message("Тікет успішно створено!", ephemeral=True)
            print(f"Ticket channel {ticket_channel.name} created for {interaction.user}.")
        except Exception as e:
            print(f"Error creating ticket channel: {e}")
            await interaction.response.send_message("Помилка створення тікету.", ephemeral=True)

# Клас для закриття тікетів
class TicketCloseView(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label="Закрити тікет", style=discord.ButtonStyle.red)
    async def close_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        print(f"Closing ticket in channel {self.channel_id}")
        try:
            channel = bot.get_channel(self.channel_id)
            await channel.send("Тікет закрито! Канал буде видалено через 7 днів.")
            tickets[self.channel_id]['closed_at'] = datetime.utcnow()
            await channel.set_permissions(interaction.guild.default_role, send_messages=False, read_messages=False)
            await interaction.response.send_message("Тікет успішно закрито!", ephemeral=True)
            print(f"Ticket in channel {self.channel_id} closed.")
        except Exception as e:
            print(f"Error closing ticket: {e}")
            await interaction.response.send_message("Помилка закриття тікету.", ephemeral=True)

# Функція для перевірки та видалення закритих тікетів
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
            del tickets[channel_id]
            print(f"Ticket log for channel {channel_id} sent to log channel.")
        except Exception as e:
            print(f"Error logging ticket deletion for channel {channel_id}: {e}")

# Основна функція для запуску бота
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
