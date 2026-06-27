import discord

from neonbot.discord_ui.embed import Embed


class TestEmbed:
    def test_default_color(self):
        embed = Embed()
        assert embed.color == discord.Colour(0xE91E63)

    def test_with_description(self):
        embed = Embed('test description')
        assert embed.description == 'test description'

    def test_add_field_returns_self(self):
        embed = Embed()
        result = embed.add_field('name', 'value')
        assert result is embed

    def test_set_author_returns_self(self):
        embed = Embed()
        result = embed.set_author(name='test')
        assert result is embed

    def test_set_footer_returns_self(self):
        embed = Embed()
        result = embed.set_footer(text='footer')
        assert result is embed

    def test_set_description_returns_self(self):
        embed = Embed()
        result = embed.set_description('desc')
        assert result is embed

    def test_set_image_none_does_not_set(self):
        embed = Embed()
        embed.set_image(url=None)
        assert not embed.image.url

    def test_set_thumbnail_none_does_not_set(self):
        embed = Embed()
        embed.set_thumbnail(url=None)
        assert not embed.thumbnail.url

    def test_set_image_valid(self):
        embed = Embed()
        embed.set_image(url='https://example.com/image.png')
        assert embed.image.url == 'https://example.com/image.png'

    def test_add_multiple_fields(self):
        embed = Embed()
        embed.add_field('f1', 'v1').add_field('f2', 'v2')
        assert len(embed.fields) == 2
