
## CPiet
___

I don't know about you but my creative outlet is Piet programming: [http://www.dangermouse.net/esoteric/piet.html](http://www.dangermouse.net/esoteric/piet.html)

Ever wanted to create complex programs with Piet -- but you just can't get the hang of it? No problem... 

CPiet is a C-based language that compiles to Piet. 

#### Syntax
The barebones syntax is defined here: [./spec.json](spec.json)
Several standard libraries have been made in the [./lib](lib/) directory.

Fibonacci Example:
```python
#include "lib/common.cpiet"

FIB_CACHE_SIZE = 100
FIB_CACHE = calloc(FIB_CACHE_SIZE)
func fib(n) {
    if (n < 2) 
        return 1
    if (n < FIB_CACHE_SIZE and FIB_CACHE[n] != 0) 
        return FIB_CACHE[n]
    
    result = fib(n - 1) + fib(n - 2)
    if (n < FIB_CACHE_SIZE) 
        FIB_CACHE[n] = result
    return result
}

func main() {
    print("Fibonacci numbers:\n")
    for (i = 0; i < 40; i += 1) 
        print("%d\n", fib(i))
}

main()
```
The compiled Piet program: [./fibonacci.png](fibonacci.png)

#### Instructions
```shell
python launch.py <cpiet filepath>
```
Use the npiet interpreter to run your compiled piet programs: [http://www.bertnase.de/npiet/](http://www.bertnase.de/npiet/)
```shell
npiet <piet output file>
```

#### Cool Features
* C-style syntax with no types
* Global variables
* Functions
* Arrays
* Variadic functions
* Common libraries (strings, lists, input/output, memory+heap management, etc...)
* Leaves out unused functions
