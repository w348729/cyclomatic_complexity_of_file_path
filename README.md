# Cyclomatic_complexity_of_file_path
This is a mini project to calculate CC of given file
cyclomatic_complexity: V(G)=e-n+2p, e is connections path of each node, n is number of nodes, p

# Running ENV
This project is using pipenv to manage the ENV
```
pipenv shell
pipenv install
```

# Installation
```
pip install git+ssh@github.com:w348729/cyclomatic_complexity_of_file_path.git

```
# Instructions
To use this module, simply import ccofp, pass in the file path as string, then call get_code_complexity() method
