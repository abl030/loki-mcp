{
  description = "AI-friendly MCP server for Grafana Loki — ~47 tools";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = {self, nixpkgs}: let
    forAllSystems = nixpkgs.lib.genAttrs [
      "x86_64-linux"
      "aarch64-linux"
    ];
  in {
    packages = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      pythonEnv = pkgs.python3.withPackages (ps: [
        ps.fastmcp
        ps.httpx
      ]);
      devPythonEnv = pkgs.python3.withPackages (ps: [
        ps.fastmcp
        ps.httpx
        ps.jinja2
        ps.pytest
        ps.pytest-asyncio
        ps.pytest-timeout
      ]);
    in {
      default = pkgs.writeShellApplication {
        name = "loki-mcp";
        runtimeInputs = [pythonEnv];
        text = ''
          exec fastmcp run ${./generated/server.py}
        '';
      };
      devShell = devPythonEnv;
    });

    devShells = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      pythonEnv = pkgs.python3.withPackages (ps: [
        ps.fastmcp
        ps.httpx
        ps.jinja2
        ps.pytest
        ps.pytest-asyncio
        ps.pytest-timeout
      ]);
    in {
      default = pkgs.mkShell {
        packages = [pythonEnv];
      };
    });
  };
}
