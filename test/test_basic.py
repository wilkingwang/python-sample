import asyncio

def generator_countdown(n):
    while n > 0:
        yield n
        n -= 1

def test_generator(n: int):
    for value in generator_countdown(n):
        print(value)

async def main():
    test_generator(5)

if __name__ == "__main__":
    asyncio.run(main())