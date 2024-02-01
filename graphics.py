from PIL import Image, ImageFont, ImageDraw, ImageEnhance


def create_progress_bar(percent: float):
    def draw_progress_bar(d, x, y, w, h, progress, bg="black", fg="blue"):
        # draw background
        d.ellipse((x+w, y, x+h+w, y+h), fill=bg)
        d.ellipse((x, y, x+h, y+h), fill=bg)
        d.rectangle((x+(h/2), y, x+w+(h/2), y+h), fill=bg)

        # draw progress bar
        w *= progress
        d.ellipse((x+w, y, x+h+w, y+h), fill=fg)
        d.ellipse((x, y, x+h, y+h), fill=fg)
        d.rectangle((x+(h/2), y, x+w+(h/2), y+h), fill=fg)

        return d

    # create image or load your existing image with out=Image.open(path)
    out = Image.new("RGBA", (150, 100), (255, 255, 255))
    draw = ImageDraw.Draw(out)

    # draw the progress bar to given location, width, progress and color
    draw = draw_progress_bar(draw, 10, 10, 100, 25, percent/100)

    datas = out.getdata()

    new_data = []
    for item in datas:
        if item[0] == 255 and item[1] == 255 and item[2] == 255:  # finding black colour by its RGB value
            # storing a transparent value when we find a black colour
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)  # other colours remain unchanged

    out.putdata(new_data)

    out.crop((0, 0, 100, 100))

    out.save("./imgs/progress.png", "PNG")
