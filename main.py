import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Додайте цю стрічку

bot = commands.Bot(command_prefix="!", intents=intents)

# Список для зберігання тікетів
tickets = {}

# Стартове повідомлення з кнопкою для створення тікету
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    channel_id = os.getenv('1250019961905217686')
    if channel_id is None:
        print("CHANNEL_ID is not set in environment variables.")
        return
    try:
        channel = bot.get_channel(int(channel_id))
        if channel is None:
            print(f"Channel with ID {channel_id} not found.")
        else:
            await channel.send(embed=discord.Embed(title="Підтримка", description="Натисніть кнопку нижче, щоб створити тікет"),
                               view=TicketCreateView())
            print(f"Message sent to channel ID {channel_id}.")
    except Exception as e:
        print(f"An error occurred: {e}")
    check_tickets.start()

class TicketCreateView(discord.ui.View):
    @discord.ui.button(label="Створити тікет", style=discord.ButtonStyle.green)
    async def create_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        ticket_channel = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name}")
        tickets[ticket_channel.id] = {
            "user": interaction.user.id,
            "created_at": datetime.utcnow()
        }
        await ticket_channel.send(f"{interaction.user.mention}, ваш тікет створено! Адміністрація скоро зв'яжеться з вами.",
                                  view=TicketCloseView(ticket_channel.id))

class TicketCloseView(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label="Закрити тікет", style=discord.ButtonStyle.red)
    async def close_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        channel = bot.get_channel(self.channel_id)
        await channel.send("Тікет закрито! Канал буде видалено через 7 днів.")
        tickets[self.channel_id]['closed_at'] = datetime.utcnow()
        await channel.set_permissions(interaction.guild.default_role, send_messages=False, read_messages=False)

@tasks.loop(minutes=1)
async def check_tickets():
    now = datetime.utcnow()
    to_delete = []
    for channel_id, ticket_info in tickets.items():
        if 'closed_at' in ticket_info and now > ticket_info['closed_at'] + timedelta(days=7):
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.delete()
            to_delete.append(channel_id)
    for channel_id in to_delete:
        log_channel = bot.get_channel(int(os.getenv('LOG_CHANNEL_ID')))  # Вставте ID вашого каналу для логів
        user = bot.get_user(tickets[channel_id]['user'])
        created_at = tickets[channel_id]['created_at']
        closed_at = tickets[channel_id]['closed_at']
        await log_channel.send(f"Тікет від {user.mention} створений {created_at} закрито {closed_at} видалено.")
        del tickets[channel_id]

def main():
    token = os.getenv('BOT_TOKEN')
    if token is None:
        raise ValueError("No BOT_TOKEN provided")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.start(token))

if __name__ == "__main__":
    main()
